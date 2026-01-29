import logging
import numpy as np

from apsbits.utils.config_loaders import get_config
from apsbits.core.instrument_init import oregistry
from bluesky.plan_stubs import mv
from bluesky.plan_stubs import sleep
from bluesky.plan_stubs import abs_set

import bluesky.preprocessors as bpp
import bluesky.plan_stubs as bps

logger = logging.getLogger(__name__)
logger.info(__file__)

softglue = oregistry["softglue"]
sample = oregistry["sample"]
socketserver = oregistry["socketserver"]
savedata = oregistry["savedata"]
eshutter = oregistry["eshutter"]

iconfig = get_config()
softglue_outputs = iconfig.get("SOFTGLUE_OUTPUTS")

# @bpp.run_decorator()
def flyscan(
    detectors,
    x_min: float = -50,  # in um
    x_max: float = 50,  # in um
    dx: float = 0.05, # in um, defaults to 50 nm
    x_npts: int | None = None,
    y_min: float = -10,  # in um
    y_max: float = 10,  # in um
    dy: float = 0.05, # in um, defaults to 50 nm
    y_npts: int | None = None,
    acquire_time: float = 50,  # in ms
    det_dead: float = 1,  # in ms (detector dead time)
    F: float = 0.9,  # Fraction of wave in straight line 0-1
    interferometer_per_pixel: int = 5, # Number of interferometry counts per image
    # interferometer_frequency: int = 1000,  # in Hz
):
    
    logging.debug("Starting flyscan")

    # --- Getting initial sample positions --- #

    x0 = sample.x.user_readback.get()
    y0 = sample.y.user_readback.get()
    z0 = sample.z.user_readback.get()

    # --- Defining flying sequence --- #

    def fly():
    
        # Temporarily fixed parameter:
        snake_npts = 1000

        # --- Defining number of points and increments --- #

        #Note, this should probably be before the fly sequence

        if x_npts is None:
            x_npts_ = int(((x_max - x_min) / dx)+1)
            dx_ = dx
        else:
            dx_ = (x_max - x_min) * 1e-3 / (max(x_npts_,2) - 1)

        if y_npts is None:
            y_npts_ = int(((y_max - y_min) / dy)+1)
            #In y, we only care about max, min and npts.
        
        logger.info(f"Starting a {x_npts_, y_npts_} flyscan. Type Ctrl+C twice to stop scan. \n Preparing stages and detectors...")

        # --- Getting initial positions --- #

        yield from bps.checkpoint()

        if not sample.y.enabled:
            sample.y.enable()

        # --- Stopping softglue and cleaning --- #

        yield from bps.checkpoint()

        logger.debug("Performing softglue cleaning.")

        softglue.stop()
        softglue.reset()
        softglue.clear_output_fields()

        # --- Defining user clock (ckUser))--- #

        yield from bps.checkpoint()

        acquire_period = acquire_time + det_dead
        interferometry_period = (acquire_period/interferometer_per_pixel) 
        user_clock_N = interferometry_period * 1e4 # Conversion from ms to the 10 MHz clock

        # user_clock_N = int(1e7 / interferometer_frequency)
        # yield from mv(softglue.div_by_n_3.n, user_clock_N)
        softglue.div_by_n_3.n.put(user_clock_N)

        logger.debug(f"Interferometry reading set at {1/(interferometry_period*1e-3) :0.3e} Hz")

        # --- Defining Image clock (ckIM)--- #

        yield from bps.checkpoint()

        trigger_period = acquire_time + det_dead
        trigger_N = trigger_period * 1e4
        # yield from mv(softglue.div_by_n_2.n, trigger_N)
        softglue.div_by_n_2.n.put(trigger_N)

        # --- Setting up gated trigger --- #

        yield from bps.checkpoint()

        yield from mv(
            softglue.gate_delay_1.in_signal,
            "ckIM",
            softglue.gate_delay_1.width,
            acquire_time * 1e4,
        )

        # --- Defining waveform clock --- #

        yield from bps.checkpoint()

        waveform_period = int(2 * trigger_period * 1e-3 * y_npts_ / (F * snake_npts * 1e-7))
        total_scan_points = max(x_npts_, 1) * snake_npts
        softglue.pulse_train.n.put(total_scan_points)
        softglue.pulse_train.period.put(waveform_period)
        softglue.pulse_train.width.put(int(waveform_period / 2))

        # --- Setting up x tweaks --- #

        yield from bps.checkpoint()

        # We set up the tweak value and the number of points
        # for the down counter

        theta = sample.theta.user_readback.get()
        logger.debug(f"Sample at {theta} degrees")

        if x_npts_>0:
            # d_value = (x_max - x_min) * 1e-3 / (max(x_npts_,2) - 1)
            _x_tweak_value = (dx_ * np.cos(-1*np.radians(theta)))*1e-3
        elif x_npts_==0:
            _x_tweak_value = 0

        yield from mv(
                sample.x.tweak_value, _x_tweak_value
            )

        yield from mv(softglue.down_counter_1.preset, x_npts_ + 1)

        # --- Setting up z tweaks --- #

        yield from bps.checkpoint()

        # We determine how much z needs to tweak per x tweak in order to keep the sample into focus
        # For safety, we limit the step to 10x that of x.

        if x_npts_>0:
            _z_tweak_value = (dx_ * np.sin(-1*np.radians(theta)))*1e-3
        elif x_npts_==0:
            _z_tweak_value=0

        yield from mv(
            sample.z.tweak_value, _z_tweak_value
        )

        ## New usage of up_down counter instead of regular downcounter
        # It doesn't interfere with the old one, so I will leave it in until we are done testing

        softglue.up_down_counter_1.preset.put(x_npts_ + 1)
        softglue.up_down_counter_1.load.put("1!")
        softglue.up_down_counter_1.updown.put("0")


        # --- Defining absolute scale for y --- #

        yield from bps.checkpoint()

        # We want the y values input by the user to be relative to the current position.
        # y_max_abs and y_min_abs has the absolute piezo position from the y_min and y_max input

        if np.abs(y_min)>45 or np.abs(y_max)>45:
            print("Requested piezo range exceeds limits. Piezos can move +/- 45 um.")
            return 
        y_min_abs = y_min + 45
        y_max_abs = y_max + 45

        # Now we calculate the threshold values for the tweaking

        _threshold_range = (y_max_abs - y_min_abs) * (1 - F)
        _positive_threshold = softglue.y_to_bits(y_max_abs - _threshold_range / 2)
        _negative_threshold = softglue.y_to_bits(y_min_abs + _threshold_range / 2)

        yield from mv(
            softglue.threshold_pos,
            _positive_threshold,
            softglue.threshold_neg,
            _negative_threshold,
        )

        # --- Centering the piezos and disabling servo stage --- #

        yield from bps.checkpoint()

        logger.debug("Enabling piezo stages analog control mode.")

        if not sample.in_analog_mode:
            sample.enable_analog_control()

        piezos_position = sample.fine_y.user_readback.get()
        # We want the piezos to be within 50 nm of the middle of the range
        if not np.isclose(piezos_position, 0.045, atol=5e-4):
            yield from softglue.move_y_analog(45)
            yield from sleep(0.5) #arbitrary since analog move has no status signal
            yield from mv(sample.y, y0)
            yield from sleep(0.5) #since on servo, we should give it some time to get there
            
        sample.y.disable()

        ## Temporarily we won't reset interferometers
        # yield from softglue.reset_interferometers()
        # logger.info("Interferometry readings reset at middle point of flyscan.")

        # --- Moving sample to scan initial position --- #

        yield from bps.checkpoint()

        # First we move y:
        yield from softglue.move_y_analog(y_min_abs)

        # # Then we move x:
        # _x = sample.x.user_readback.get()
        if x_npts_>0:
            step_x = x_min * 1e-3 - _x_tweak_value
            _starting_x = x0 + step_x
            yield from mv(sample.x, _starting_x)

            logger.debug(f"Samply X stage moved to {_starting_x*1e3:0.3e} um.")

            # Finally, we move z:
            step_z = sample.compensating_z(dx_)
            _starting_z = z0 + step_z
            yield from mv(sample.z, _starting_z)

            logger.debug(f"Samply Z stage moved to {_starting_z*1e3:0.3e} um.")


        # --- Load waveform --- #

        yield from bps.checkpoint()

        logging.debug("Loading waveform.")

        yield from softglue.enable_waveform()
        yield from softglue.snake_y(y_min=y_min_abs, y_max=y_max_abs, F=F, npts=snake_npts)

        logging.debug("Flyscan waveform loaded.")
        softglue.dac1_write.put("funcGenPulse")

        # --- Update savedata's scan number --- #

        yield from bps.checkpoint()

        savedata.advance_scan_number()

        # --- Preparing socket server --- #

        yield from bps.checkpoint()

        total_images = int((max(x_npts_, 1) * y_npts_) / F - 1)
        images_per_line = int(y_npts_ / F)
        interferometry_per_line = images_per_line * interferometer_per_pixel
        total_lines = total_images*(interferometer_per_pixel+1) # We add one to leave room for events in which more frames per line are reached

        # socketserver.setup_flyscan_mode(num_lines = total_lines)
        # We are changing to the new structure in which we have as many position files as detector files
        socketserver.setup_flyscan_mode(hdf_images=interferometry_per_line)
        socketserver.stage()
        socketserver.trigger()

        # --- Arm detectors --- #

        yield from bps.checkpoint()

        logging.debug("Arming detectors")

        for detector in detectors:
            # To follow correct bluesky procedure, we need to change towards using Prepare instead of stage. We should stage before the open run document is generated
            softglue.enable_detector_trigger(detector.name)
            detector.setup_flyscan_mode(
                num_images=total_images,
                acq_time=acquire_time * 1e-3,
                hdf_images=images_per_line,
            )
            detector.stage()

        # --- Open shutter --- #

        yield from bps.open_run()

        yield from bps.checkpoint()

        logger.debug("Opening shutter.")

        yield from abs_set(eshutter, "open", wait=True)

        # --- Start softglue --- #

        softglue.prepare()

        logging.info("Takeoff!")

        yield from bps.trigger(softglue, wait=True)

    def cleanup():

        logger.info("Flyscan done. Disarming detectors and returning to original position.")

        # --- Close shutter ---#

        logger.debug("Closing shutter.")

        yield from abs_set(eshutter, "close", wait=True)

        # --- Unstage detectors --- #

        logging.debug("Scanning done.")

        for detector in detectors:
            detector.unstage()
            detector.hdf1.unstage()

        socketserver.unstage()

        # --- Filling up DMA for socket server acquisition --- #

        logger.debug("Flushing the DMA")

        for i in range(11):
            softglue.scal_to_stream_1.flush.put("1!")
            yield from sleep(0.1)

        socketserver.unstage()

        # --- Return sample to initial positions ---

        yield from softglue.move_y_analog(45)
        sample.y.enable()
        yield from mv(sample.x, x0,
                    sample.y, y0,
                    sample.z, z0)
        

        logger.debug("Returning to original positions.")

        # --- Softglue cleanup ---

        softglue.up_down_counter_1.load.put("1!")
        softglue.stop()
        softglue.reset()
        softglue.clear_output_fields()

        logger.debug("Performing softglue cleanup.")

        yield from bps.close_run()

    yield from bpp.finalize_wrapper(fly(), cleanup())
    # yield from fly()

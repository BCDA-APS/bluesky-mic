import logging
import numpy as np

from apsbits.utils.config_loaders import get_config
from apsbits.core.instrument_init import oregistry
from bluesky.plan_stubs import mv
from bluesky.plan_stubs import sleep
from bluesky.plan_stubs import abs_set

import bluesky.preprocessors as bpp
import bluesky.plan_stubs as bps

from ..utils.run_engine import RE

logger = logging.getLogger(__name__)
logger.info(__file__)

softglue = oregistry["softglue"]
softglue2 = oregistry["softglue2"]
sample = oregistry["sample"]
socketserver = oregistry["socketserver"]
socketserver2 = oregistry["socketserver2"]
savedata = oregistry["savedata"]
eshutter = oregistry["eshutter"]
fast_shutter = oregistry["fast_shutter"]

iconfig = get_config()
# softglue_outputs = iconfig.get("SOFTGLUE_OUTPUTS")

# @bpp.run_decorator() # To just use this we need to rewrite the staging methods in the detectors to no start acquiring and implementing a kickoff function
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
    det_dead: float = 0.1,  # in ms (detector dead time)
    F: float = 0.9,  # Fraction of wave in straight line 0-1
    interferometer_per_pixel: int = 5, # Number of interferometry counts per image
    # interferometer_frequency: int = 1000,  # in Hz
    ptycho: bool = False,
):
    
    logging.debug("Starting flyscan")

    # --- Resolving number of points and step sizes --- #

    if F <= 0 or F > 1:
        raise ValueError("F must be between 0 and 1.")

    if x_npts is None:
        x_npts_ = abs(int(((x_max - x_min) / dx) + 1))
        dx_ = dx
    else:
        x_npts_ = abs(x_npts)
        dx_ = (x_max - x_min) / (max(x_npts_, 2) - 1)

    if np.abs(y_min)>45 or np.abs(y_max)>45:
            raise ValueError("Requested piezo range exceeds limits. Piezos can move +/- 45 um.")

    if y_npts is None:
        y_npts_ = abs(int(((y_max - y_min) / dy) + 1))
        dy_ = dy
    else:
        y_npts_ = abs(y_npts)
        dy_ = (y_max - y_min) / (max(y_npts_, 2) - 1)

    # --- Capturing plan arguments for metadata --- #

    plan_args = {
        "detectors": [d.name for d in detectors],
        "x_min": x_min,
        "x_max": x_max,
        "dx": dx_,
        "x_npts": x_npts_,
        "y_min": y_min,
        "y_max": y_max,
        "dy": dy_,
        "y_npts": y_npts_,
        "acquire_time": acquire_time,
        "det_dead": det_dead,
        "F": F,
        "interferometer_per_pixel": interferometer_per_pixel,
        "ptycho": ptycho,
    }

    # --- Getting initial sample positions --- #

    x0 = sample.x.user_readback.get()
    y0 = sample.y.user_readback.get()
    z0 = sample.z.user_readback.get()

    # --- Verifying detectors are unstaged - - - #

    for detector in detectors:
        detector.unstage()
        detector.hdf1.unstage()

    # --- Defining flying sequence --- #

    def fly():
    
        # Temporarily fixed parameter:
        snake_npts = 1000

        eta = (x_npts_ * y_npts_ * acquire_time / 1000 / F) / 60 #time in minutes
        print(f'\nStarting flyscan. ETA {np.around(eta, 2)} minutes')
        
        logger.info(f"Starting a {x_npts_, y_npts_} flyscan. Type Ctrl+C twice to stop scan. \n Preparing stages and detectors...")

        # --- Getting initial positions --- #

        yield from bps.checkpoint()

        if not sample.y.enabled:
            sample.y.enable()

        # --- Stopping softglue and cleaning --- #

        yield from bps.checkpoint()

        logger.debug("Performing softglue cleaning.")

        # --- Coupling softglue boards --- #

        # softglue.io.fo5.put('enable')
        # softglue.io.fo6.put('enable1')
        # softglue.io.fo7.put('reset')
        # softglue.io.fo8.put('ck1MHz')

        # softglue2.io.fi9.put('enable')
        # softglue2.io.fi10.put('enable1')
        # softglue2.io.fi11.put('reset')
        # softglue2.io.fi12.put('ck1MHz2')

        softglue.stop()
        softglue.reset()
        softglue.clear_output_fields(exception=[5, 6, 7, 8])
        softglue2.clear_output_fields()

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

        trigger_N = acquire_period * 1e4
        # yield from mv(softglue.div_by_n_2.n, trigger_N)
        softglue.div_by_n_2.n.put(trigger_N)
        softglue2.div_by_n_2.n.put(trigger_N)

        # --- Setting up gated trigger --- #

        yield from bps.checkpoint()

        yield from mv(
            softglue.gate_delay_1.in_signal, "ckIM",
            softglue.gate_delay_1.width, acquire_time * 1e4,
            softglue2.gate_delay_1.in_signal, "ckIM",
            softglue2.gate_delay_1.width, acquire_time * 1e4,
        )

        # --- Setting up 2nd Softglue User Clock and Clear signals --- #

        det_dead_sections = int(det_dead/5)

        yield from mv(
            softglue2.gate_delay_2.in_signal, "ckIM",
            softglue2.gate_delay_2.out_signal, "ckUser",
            softglue2.gate_delay_2.width, det_dead_sections * 1e4,
            softglue2.gate_delay_2.delay, (acquire_time+1*det_dead_sections) * 1e4,
            softglue2.gate_delay_3.in_signal, "ckIM",
            softglue2.gate_delay_3.out_signal, "clear",
            softglue2.gate_delay_3.width, det_dead_sections * 1e4,
            softglue2.gate_delay_3.delay, (acquire_time+3*det_dead_sections) * 1e4,
        )

        # --- Defining waveform clock --- #

        yield from bps.checkpoint()

        waveform_period = int(2 * acquire_period * 1e-3 * y_npts_ / (F * snake_npts * 1e-7))
        total_scan_points = max(x_npts_, 1) * snake_npts
        softglue.pulse_train.n.put(total_scan_points)
        softglue.pulse_train.period.put(waveform_period)
        softglue.pulse_train.width.put(int(waveform_period / 2))

        # --- Setting up x tweaks --- #

        yield from bps.checkpoint()

        # We set up the tweak value and the number of points
        # for the down counter

        if ptycho:
            theta = 0
        else:
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
            x_min_angled = (x_min * np.cos(-1*np.radians(theta)))
            # print(f'x_min_angled = {x_min_angled}')
            step_x = x_min_angled*1e-3 - _x_tweak_value
            # print(f'step_x={step_x}')
            _starting_x = x0 + step_x
            # print(f'{_starting_x=}')
            yield from mv(sample.x, _starting_x)

            logger.debug(f"Samply X stage moved to {_starting_x*1e3:0.3e} um.")

            # Finally, we move z:
            if not ptycho:
                step_z = sample.compensating_z(x_min) * 1e-3
                _starting_z = z0 + step_z - _z_tweak_value
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

        # savedata.advance_scan_number()
        savedata.next_scan_number.put(RE.md['scan_id']+1)

        # --- Preparing socket server --- #

        yield from bps.checkpoint()

        total_images = int((max(x_npts_, 1) * y_npts_) / F - 1)
        images_per_line = int(y_npts_ / F)
        interferometry_per_line = images_per_line * interferometer_per_pixel
        # total_lines = total_images*(interferometer_per_pixel+1) # We add one to leave room for events in which more frames per line are reached

        # socketserver.setup_flyscan_mode(num_lines = total_lines)
        # We are changing to the new structure in which we have as many position files as detector files
        socketserver.setup_flyscan_mode(hdf_images=interferometry_per_line)
        socketserver.stage()
        yield from bps.sleep(1)
        socketserver.trigger()
        yield from bps.sleep(1)

        socketserver2.setup_flyscan_mode(hdf_images=interferometry_per_line)
        socketserver2.stage()
        yield from bps.sleep(1)
        socketserver2.trigger()
        yield from bps.sleep(1)

        # --- Arm detectors --- #

        yield from bps.checkpoint()

        logging.debug("Arming detectors")

        for detector in detectors:
            # To follow correct bluesky procedure, we need to change towards using Prepare instead of stage. We should stage before the open run document is generated
            softglue.enable_detector_trigger(detector.name)
            softglue2.enable_detector_trigger(detector.name)
            detector.setup_flyscan_mode(
                num_images=total_images,
                acq_time=acquire_time * 1e-3,
                hdf_images=images_per_line,
            )
            detector.stage()

        # # --- Coupling softglue boards --- #

        # softglue.io.fo5.put('enable')
        # softglue.io.fo6.put('enable1')
        # softglue.io.fo7.put('reset')
        # softglue.io.fo8.put('ck1MHz')

        # softglue2.io.fi9.put('enable')
        # softglue2.io.fi10.put('enable1')
        # softglue2.io.fi11.put('reset')
        # softglue2.io.fi12.put('ck1MHz2')

        # --- Clearing 2nd softglue dma --- #

        yield from mv(softglue2.dma.enable, 1)
        yield from mv(softglue2.dma.clear_button, 1)
        yield from mv(softglue2.dma.clear_buffer, 1)
        yield from sleep(1)

        # --- Open shutter --- #

        yield from bps.open_run(md={"plan_args": plan_args})

        yield from bps.checkpoint()

        logger.debug("Opening shutter.")

        yield from abs_set(eshutter, "open", wait=True)

        yield from bps.sleep(3)

        fast_shutter.open()

        yield from bps.sleep(0.1)

        # --- Start softglue --- #

        softglue.prepare()

        logging.info("Takeoff!")

        yield from bps.trigger(softglue, wait=True)

    def cleanup():

        logger.info("Flyscan done. Disarming detectors and returning to original position.")

        # --- Close shutter ---#

        logger.debug("Closing shutter.")

        yield from abs_set(eshutter, "close", wait=True)

        fast_shutter.close()

        # --- Filling up DMA for socket server acquisition --- #

        logger.debug("Flushing the DMA")

        for _ in range(11):
            softglue.scal_to_stream_1.flush.put("1!")
            yield from sleep(0.1)

        # We leave sufficient time for the socket server to finish acquiring the last images before unstaging it
        yield from sleep(2)

        socketserver.unstage()

        for _ in range(11):
            softglue2.scal_to_stream_1.flush.put("1!")
            yield from sleep(0.1)

        socketserver2.unstage()
        

        logger.debug("Returning to original positions.")

        # --- Return sample to initial positions ---

        yield from softglue.move_y_analog(45)
        sample.y.enable()
        yield from mv(sample.x, x0,
                    sample.y, y0,
                    sample.z, z0)

        # --- Unstage detectors --- #

        logging.debug("Scanning done.")

        for detector in detectors:
            detector.unstage()
            detector.hdf1.unstage()


        # --- Softglue cleanup ---

        softglue.up_down_counter_1.load.put("1!")
        softglue.stop()
        softglue.reset()
        softglue.clear_output_fields()
        softglue.up_down_counter_1.load.put("1!")
        softglue.stop()
        softglue.reset()
        softglue.clear_output_fields(exception=[5, 6, 7, 8])
        # Redundant cleanup to ensure softglue is stopped and cleared.

        logger.debug("Performing softglue cleanup.")

        yield from bps.close_run()

    yield from bpp.finalize_wrapper(fly(), cleanup())

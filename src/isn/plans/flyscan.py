from apsbits.utils.controls_setup import oregistry
from apsbits.utils.config_loaders import get_config
from bluesky.plan_stubs import mv, sleep
import logging

logger = logging.getLogger(__name__)
logger.info(__file__)

softglue = oregistry['softglue']
sample = oregistry['sample']
socketserver = oregistry['socketserver']
savedata = oregistry['savedata']

# ptycho = oregistry['ptycho'] #temporary while we fix external gating
# xrd = oregistry['xrd'] #temporary while we fix external gating


iconfig = get_config()
softglue_outputs = iconfig.get("SOFTGLUE_OUTPUTS")

def flyscan(
        detectors,
        x_min:float =-50, # in um
        x_max:float =50, #in um
        x_npts:int =11,
        y_min:float =0, #in um
        y_max:float =90, #in um
        y_npts:int =11,
        acquire_time:float =80, # in ms
        det_dead:float =20, # in ms (detector dead time)
        F:float =0.9, # Fraction of wave in straight line 0-1
        interferometer_frequency: int = 1000 #in Hz
):
    
    #Temporarily fixed parameter:
    snake_npts=1000
    
    # --- Stopping softglue and cleaning --- #

    logger.info("Performing softglue cleaning.")

    yield from softglue.stop()
    yield from softglue.reset()
    softglue.clear_output_fields()


    # --- Defining user clock (ckUser))--- #

    user_clock_N = 1e7/interferometer_frequency
    yield from mv(softglue.div_by_n_3.n, user_clock_N)

    logger.info(f"Interferometry reading set at {interferometer_frequency :0.3e} Hz")


    # --- Defining Image clock (ckIM)--- #

    trigger_period = acquire_time+det_dead
    trigger_N = trigger_period*1e4
    yield from mv(softglue.div_by_n_2.n, trigger_N)


    # --- Setting up gated trigger --- #

    yield from mv(
        softglue.gate_delay_1.in_signal, "ckIM",
        softglue.gate_delay_1.width, acquire_time*1e4
    )


    # --- Defining waveform clock --- #

    waveform_period = 2*trigger_period*1e-3*y_npts/(F*snake_npts*1e-7)
    total_scan_points = x_npts*snake_npts
    softglue.pulse_train.n.put(total_scan_points)
    softglue.pulse_train.period.put(waveform_period)
    softglue.pulse_train.width.put(int(waveform_period/2))


    # --- Setting up x tweaks --- #

    # We set up the tweak value and the number of points 
    # for the down counter
    _x_tweak_value = (x_max-x_min)*1e-3/(x_npts-1)
    yield from mv(sample.x.tweak_value, _x_tweak_value,
                  softglue.down_counter_1.preset, x_npts+1 
                  )
    
    yield from mv(softglue.down_counter_1.preset, x_npts+1)
    
    # Now we calculate the threshold values for the tweaking

    _threshold_range = (y_max-y_min)*(1-F)
    _positive_threshold = softglue.y_to_bits(y_max-_threshold_range/2)
    _negative_threshold = softglue.y_to_bits(y_min+_threshold_range/2)

    yield from mv(softglue.threshold_pos, _positive_threshold,
                  softglue.threshold_neg, _negative_threshold)


    # --- Moving y stage to center range position --- #

    # We always position at the center of the range :
    sample.enable_analog_control()
    yield from sleep(10)
    y_cen = (y_max+y_min)/2
    yield from softglue.move_y_analog(45)
    yield from sleep(1)

    # logger.info(f"Samply Y stage moved to {y_cen:0.3e} um.")
    logger.info(f"Samply Y stage moved to {45} um.")


    # yield from softglue.disable_waveform()
    # y_cen_bits = softglue.y_to_bits(y_cen)
    # softglue.dac1_val.put(y_cen_bits)
    # softglue.dac1_write.put("1!")
    # softglue.dac1_write.put("funcGenPulse")

    # logger.info("Softglue DAC output set to match y-position.")


    yield from softglue.reset_interferometers()

    logger.info("Interferometry readings reset at middle point of flyscan.")


    # --- Moving sample to scan initial position --- #

    #First we move y:

    yield from softglue.move_y_analog(y_min)

    # Then we move x:

    _x = sample.x.user_readback.get()
    _starting_x = _x+x_min*1e-3-_x_tweak_value
    yield from mv(sample.x, _starting_x)

    logger.info(f"Samply X stage moved to {_starting_x*1e3:0.3e} um.")



    

    # --- Enabling y stage analog control --- #

    # sample.enable_analog_control()
    # yield from sleep(5)

    logger.info("Softglue has taken over y-stage control.")



    # --- Load waveform --- #

    yield from softglue.enable_waveform()
    yield from softglue.snake_y(y_min=y_min, y_max=y_max, F=F, npts=snake_npts)

    logging.info("Flyscan waveform loaded.")
    softglue.dac1_write.put("funcGenPulse")


    # --- Preparing socket server --- #

    socketserver.stage()
    socketserver.trigger()


    # --- Arm detectors --- #


    logging.info("Arming detectors")

    total_images = int((x_npts*y_npts)/F-1)
    logging.info(f"Expecting {total_images} images.")

    for detector in detectors:

        softglue.enable_detector_trigger(detector.name)
        
        # if detector in [ptycho, xrd]: #temporary patch while we fix external gating mode
        #     total_images = int((x_npts*y_npts)/F-1)
        #     detector.setup_flyscan_mode(num_images=total_images)
        #     logging.info(f"Expecting {total_images} images.")
        # else:
        #     detector.setup_flyscan_mode()

        detector.setup_flyscan_mode(num_images=total_images, 
                                    acq_time=acquire_time*1e-3,
                                    hdf_images=int(y_npts/0.9))
        # detector.hdf1.stage()
        detector.stage()

        

    # --- Start softglue --- #

    sample.enable_analog_control()

    logging.info("Takeoff!")

    yield from softglue.start_flyscan()


    # --- Unstage detectors --- #

    logging.info("Scanning done.")
    print("Scanning done.")


    for detector in detectors:
        detector.unstage()
        detector.hdf1.unstage()
    
    # --- Filling up DMA for socket server acquisition --- #

    print("Flushing the DMA")

    yield from sleep(3)

    for i in range(11):
        softglue.scal_to_stream_1.flush.put("1!")
        yield from sleep(1)
    # arrays_after_scan = socketserver.array_counter.get()

    # while arrays_after_scan == socketserver.array_counter.get():
    #     softglue.scal_to_stream_1.flush.put("1!")
    #     yield from sleep(0.05)


    socketserver.unstage()


    # --- Update savedata's scan number --- #

    savedata.advance_scan_number()

    # --- Return sample to initial positions ---


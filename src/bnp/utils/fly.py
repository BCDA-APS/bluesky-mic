import logging

logger = logging.getLogger(__name__)

def setup_detectors_and_fileio(
        devices, 
        num_pulses:int = None, 
        dwell_time:float = None, 
        stepsize: float = None, 
        motor_resolution: float = None,
        ptycho_exp_factor: float = 1,
        eiger_trigger_mode: int = 2,
        **kwargs
):
    """
    Setup the detectors and file I/O for the flyscan plan.
    
    Parameters
    ----------
    devices : list
        List of ophyd devices
    num_pulses : int
        Number of pulses for the scan
    dwell_time : float
        Dwell time for the scan in ms
    stepsize : float
        Step size for the scan in x direction
    motor_resolution : float
        Motor resolution for the scan
    eiger_trigger_mode : int
        Eiger trigger mode: 3 for External Enable or 2 for External
        Series. Default is 2.
    """


    for det in devices:
        det_dwell_time = (dwell_time / ptycho_exp_factor if det.name == "eiger" else dwell_time) / 1000 # convert to seconds
        if det.name == "xmap":
            det.unstage()
            # update num_capture for xmap fileplugin    
            det.cam.calc_num_capture(num_pulses)
            try:
                det.fileplugin.config_file_writer(det.cam.num_capture, **kwargs)
            except Exception as e:
                logger.error(f"Error configuring fileplugin for fly scan: {e}")
                raise e
        else:
            config_kwargs = {
                "num_pulses": num_pulses,
                "dwell_time": det_dwell_time,
                "stepsize": stepsize,
                "motor_resolution": motor_resolution,
            }
            if det.name == "eiger":
                config_kwargs["trigger_mode"] = eiger_trigger_mode
            det.config_flyscan(**config_kwargs)

        det.stage()

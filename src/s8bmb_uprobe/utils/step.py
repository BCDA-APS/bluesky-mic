

def setup_detectors_and_fileio(
        devices, 
        num_pulses:int = 1, 
        dwell_time:float = None, 
        stepsize: float = None, 
        motor_resolution: float = None,
):
    """
    Setup the detectors for step scan.
    No FileIO has been configured for step scan yet...
    Please configure the FileIO manually if needed.
    
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
    """

    for det in devices:
        det.config_stepscan(
            num_pulses=num_pulses,
            dwell_time=dwell_time,
        )
        det.stage()
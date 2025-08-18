"""
Creating a bluesky plan that does not use Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    fly2d
""".split() 

import logging
import bluesky.plan_stubs as bps
from apsbits.core.instrument_init import oregistry
from apsbits.utils.config_loaders import get_config
from s2idd_uprobe.plans.before_after_fly import setup_flyscan_SIS3820_XMAP
from s2idd_uprobe.plans.fly1d_noScanRecord import fly1d
import numpy as np
from ophyd.status import Status
from apstools.plans import run_blocking_function



logger = logging.getLogger(__name__)

sis3820 = oregistry["sis3820"]
savedata = oregistry["savedata"]
xrf = oregistry["xrf"]
xrf_netcdf = oregistry["xrf_netcdf"]

samx = oregistry["samx"]
samy = oregistry["samy"]
samz = oregistry["samz"]

iconfig = get_config()
scan_overhead = iconfig.get("SCAN_OVERHEAD")
netcdf_delimiter = iconfig.get("FILE_DELIMITER")
xmap_buffer = iconfig.get("XMAP")["BUFFER"]

det_foldername = {"xrf": "flyXRF", "preamp1": "tetramm", "preamp2": "tetramm2"}

def fly2d(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
    height=0,
    y_center=None,
    stepsize_y=0,
    dwell=0,
    sample_z=None,
    inc_eng=None,
    adjust_zp=False,
    xrf_on=True,
    preamp1_on=False,
    preamp2_on=False,
):
    
    """
    Fly 2D scan that does not rely on Scan Record. 

    The detail scan plan is as follows:
    Before the scan loop:
        1. Setup struck SIS3820 based on the number of scan points and dwell time.
        2. Setup the sample z position.

    In the scan loop, indented by inner and outer loops:
        - Drive the y-motor to start position (y_center - height/2)
        - Arm and setup proper filePlugin for selected detectors
            - Drive x-motor to the start position (x_center - width/2)
            - Adjust x-motor speed to the desired speed
            - Drive x-motor to the end position (x_center + width/2)
            - Adjust to fast x-motor speed
            - Drive x-motor to the start position (x_center - width/2)

    Parameters
    ----------
    samplename :
        Str: The name of the sample.
    user_comments :
        Str: The user comments for the scan.
    width :
        Float: The width of the scan.
    x_center :
        Float: The center of the scan in the x-direction. If not provided, the current x-motor position will be used.
    stepsize_x :
        Float: The step size of the scan in the x-direction.
    height :
        Float: The height of the scan.
    y_center :
        Float: The center of the scan in the y-direction. If not provided, the current y-motor position will be used.
    stepsize_y :
        Float: The step size of the scan in the y-direction.
    dwell :
        Float: The dwell time of the scan.
    sample_z :
        Float: The sample z position.
    inc_eng :
        Float: The increment in energy.
    adjust_zp :
        Bool: Whether to adjust the zero point.
    xrf_on :
        Bool: Whether to turn on the x-ray fluorescence.
    preamp1_on :
        Bool: Whether to turn on the preamp1.
    preamp2_on :
        Bool: Whether to turn on the preamp2.
    """

    """Check input parameters and detector status"""
    if any([stepsize_y == 0, stepsize_x == 0]):
        raise ValueError("Step size cannot be 0, please check the input parameters")

    devices = [sis3820, xrf, xrf_netcdf]
    for device in devices:
        if not device.connected:
            raise ValueError(f"{device.name} is not connected, please check the status")
    
    """Setup the sample z, x, and y position"""
    if sample_z is not None:
        yield from bps.mv(samz, sample_z)
    if x_center is None:
        yield from bps.mv(samx, samx.position - width/2)
    if y_center is not None:
        yield from bps.mv(samy, samy.position - height/2)

    """Construct the scan points and calculate the motor speeds"""
    yarr = np.arange(y_center - height/2, y_center + height/2, stepsize_y)
    xarr = np.arange(x_center - width/2, x_center + width/2, stepsize_x)
    x_motor_scan_speed = samx.calculate_scan_speed(stepsize_x, dwell)
    x_motor_retrace = samx.get_max_velocity()

    """Setup detectors and file IO"""
    numpts_x = len(xarr)
    num_pulses = numpts_x - 2

    savedata.update_next_file_name()
    next_file_name = savedata.next_file_name
    filename = next_file_name.replace(".mda", "")

    # Setup the SIS3820 and XMAP (XRF)
    yield from setup_flyscan_SIS3820_XMAP(sis3820, xrf, stepsize_x, num_pulses)

    # Setup the XRF netCD
    num_capture = int(np.ceil(num_pulses / xmap_buffer))

    yield from xrf_netcdf.setup_file_writer(
        savedata,
        det_foldername["xrf"],
        num_capture,
        filename=filename,
        beamline_delimiter=netcdf_delimiter,
    )
    
    x_start = xarr[0]
    x_end = xarr[-1]
    yield from bps.mv(samx.velocity, x_motor_retrace)
    yield from bps.mv(samx, x_start)
    yield from bps.mv(samx.velocity, x_motor_scan_speed)
    

    # Drive the y-motor to the start position
    for i, y in enumerate(yarr):

        logger.info(f"Moving to y = {y}")
        logger.info(f"x_motor velocity = {samx.velocity.get()}")
        yield from bps.mv(samy, y)

        if i == 0:
            print("Open shutter")
            yield from savedata.set_next_scan_number(savedata.next_scan_number.get() + 1)

        #TODO: try to use fly1d plan to replace the following code
        yield from fly1d()

        ready = Status()
        def wait(old_value, value, **kwargs):
            if old_value == 1 and value == 0:
                ready.set_finished()
                xrf_netcdf.capture.unsubscribe(wait)

        xrf_netcdf.capture.subscribe(wait)
        
        yield from xrf_netcdf.set_capture("CAPTURING")
        yield from xrf.set_erase_start(1)
        yield from sis3820.set_erase_start(1)

        yield from bps.sleep(0.2)
        yield from bps.mv(samx, x_end)
        yield from run_blocking_function(ready.wait)

        yield from bps.mv(samx.velocity, x_motor_retrace)
        yield from bps.mv(samx, x_start)
        



    
    
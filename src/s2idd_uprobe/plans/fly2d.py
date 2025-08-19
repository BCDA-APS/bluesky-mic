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
from s2idd_uprobe.plans.flyscan_core import (
    setup_detectors_and_fileio,
    setup_motor_positions_and_speeds,
    create_file_done_signal,
    validate_scan_parameters,
    validate_device_connections,
    calculate_x_scan_parameters
)
from s2idd_uprobe.plans.fly1d import fly1d
from s2idd_uprobe.plans.toggle_usercalc import disable_usercalc
from s2idd_uprobe.plans.toggle_usercalc import enable_usercalc
import numpy as np

logger = logging.getLogger(__name__)

savedata = oregistry["savedata"]
samx = oregistry["samx"]
samy = oregistry["samy"]
samz = oregistry["samz"]

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

    """Disable usercalc"""
    yield from disable_usercalc()

    """Check input parameters and detector status"""
    validate_scan_parameters(stepsize_x, stepsize_y)
    validate_device_connections()
    
    """Setup the sample z, x, and y position"""
    if sample_z is not None:
        yield from bps.mv(samz, sample_z)
    if x_center is None:
        yield from bps.mv(samx, samx.position - width/2)
    if y_center is not None:
        yield from bps.mv(samy, samy.position - height/2)

    """Construct the scan points and calculate the motor speeds"""
    yarr = np.arange(y_center - height/2, y_center + height/2, stepsize_y)
    # Calculate scan parameters
    xarr, x_start, x_end, x_motor_scan_speed, x_motor_retrace, num_pulses = calculate_x_scan_parameters(
        width, x_center, stepsize_x, dwell
    )

    """Setup detectors and file IO"""
    numpts_x = len(xarr)
    num_pulses = numpts_x - 2

    # Setup detectors and file I/O
    filename = yield from setup_detectors_and_fileio(stepsize_x, num_pulses, samx.resolution.get())
    
    # Setup motor positions and speeds
    yield from setup_motor_positions_and_speeds(x_start, x_motor_scan_speed, x_motor_retrace)
    
    # Create file done signal
    ready = create_file_done_signal()
    unsubscribe = False

    # Drive the y-motor to the start position
    for i, y in enumerate(yarr):

        logger.info(f"Moving to y = {y}")
        yield from bps.mv(samy, y)

        yield from bps.mv(samx.velocity, x_motor_scan_speed)
        logger.info(f"x_motor velocity = {samx.velocity.get()}")

        if i == 0:
            print("Open shutter")
            yield from savedata.set_next_scan_number(savedata.next_scan_number.get() + 1)
        if y == yarr[-1]:
            unsubscribe = True

        yield from fly1d(x_end=x_end, x_start=x_start, 
                        x_motor_retrace=x_motor_retrace, ready=ready, unsubscribe=unsubscribe)
        yield from bps.sleep(0.2)
        
    # xrf_netcdf.capture.unsubscribe(wait)
    yield from bps.mv(samx.velocity, x_motor_retrace)
    

    """Enable usercalc"""
    yield from enable_usercalc()

# RE(fly2d(width = 10, x_center = 5281, stepsize_x=0.1, height = 10, y_center = -2200, stepsize_y=1, dwell=100, sample_z=0, xrf_on=True, preamp1_on=False, preamp2_on=False))

    
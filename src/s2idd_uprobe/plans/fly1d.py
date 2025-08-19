"""
Fly1D plan for 2idd. A building block for fly2d_noScanRecord plan

@author: yluo(grace227)
"""

import bluesky.plan_stubs as bps
from apsbits.core.instrument_init import oregistry
from apstools.plans import run_blocking_function
from s2idd_uprobe.plans.flyscan_core import (
    setup_detectors_and_fileio,
    setup_motor_positions_and_speeds,
    create_file_done_signal,
    calculate_x_scan_parameters
)
import inspect
import logging
import numpy as np
from ophyd.status import Status

logger = logging.getLogger(__name__)

savedata = oregistry["savedata"]
samx = oregistry["samx"]
sis3820 = oregistry["sis3820"]
xrf = oregistry["xrf"]
xrf_netcdf = oregistry["xrf_netcdf"]

def fly1d(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
    dwell=0,
    sample_z=None,
    xrf_on=True,
    preamp1_on=False,
    preamp2_on=False,
    x_end=None,
    x_start=None,
    x_motor_retrace=None,
    x_motor_scan_speed=None,
    ready=None,
    unsubscribe=False,
):
    """
    Fly 1D scan that does not rely on Scan Record.

    This plan is a building block for fly2d_noScanRecord plan. 
    When called from anyone except plan_mutator, this fly1D plan will be commanding:
    - detectors to capture
    - get struck3820 to be ready
    - move the x-motor to the end position
    - wait until detector files are saved
    - retrace the x-motor to the start position

    When called from plan_mutator, this fly1D plan will:
    - calculate the scan points and the motor speeds
    - setup detectors and file IO
    - perform the same steps as the caller from the non plan_mutator plan

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
    dwell :
        Float: The dwell time of the scan.
    sample_z :
        Float: The sample z position. If not provided, the current sample z position will be used.
    xrf_on :
        Bool: Whether to turn on the x-ray fluorescence detector.
    preamp1_on :
        Bool: Whether to turn on the preamp1.
    preamp2_on :
        Bool: Whether to turn on the preamp2.
    """

    """Check who is calling the function"""
    caller_name = "unknown"
    current_frame = inspect.currentframe()
    if current_frame and current_frame.f_back:
        caller_name = current_frame.f_back.f_code.co_name
        logger.info(f"Called from {caller_name}")
    
    
    if caller_name == "plan_mutator":
        logger.info(f"Called from {caller_name}")
        
        # Calculate scan parameters
        xarr, x_start, x_end, x_motor_scan_speed, x_motor_retrace, num_pulses = calculate_x_scan_parameters(
            width, x_center, stepsize_x, dwell
        )

        # Setup detectors and file I/O
        filename = yield from setup_detectors_and_fileio(stepsize_x, num_pulses, samx.resolution.get())
        
        # Setup motor positions and speeds
        yield from setup_motor_positions_and_speeds(x_start, x_end, x_motor_scan_speed, x_motor_retrace)

        # Create file done signal
        ready = create_file_done_signal()

        yield from savedata.set_next_scan_number(savedata.next_scan_number.get() + 1)
        yield from _fly1d(xrf_netcdf, xrf, sis3820, samx, x_end, x_start, 
                          x_motor_retrace, ready)
        
        yield from bps.sleep(0.2)


    else:
        yield from _fly1d(xrf_netcdf, xrf, sis3820, samx, x_end, x_start, 
                          x_motor_retrace, ready)
        if unsubscribe:
            xrf_netcdf.capture.unsubscribe_all()

    


def _fly1d(xrf_netcdf, xrf, sis3820, samx, x_end, x_start, 
            x_motor_retrace, ready):

    yield from xrf_netcdf.set_capture("CAPTURING")
    yield from xrf.set_erase_start(1)
    yield from sis3820.set_erase_start(1)

    yield from bps.sleep(0.2)
    yield from bps.mv(samx, x_end)
    yield from run_blocking_function(ready.wait)

    yield from bps.mv(samx.velocity, x_motor_retrace)
    yield from bps.mv(samx, x_start)
    
        







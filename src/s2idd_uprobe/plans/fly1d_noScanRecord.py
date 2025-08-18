"""
Fly1D plan for 2idd. A building block for fly2d_noScanRecord plan

@author: yluo(grace227)
"""

import bluesky.plan_stubs as bps
from apsbits.core.instrument_init import oregistry
from apsbits.utils.config_loaders import get_config
import inspect
import logging

logger = logging.getLogger(__name__)


sis3820 = oregistry["sis3820"]
savedata = oregistry["savedata"]
xrf = oregistry["xrf"]
xrf_netcdf = oregistry["xrf_netcdf"]
samx = oregistry["samx"]

iconfig = get_config()
netcdf_delimiter = iconfig.get("FILE_DELIMITER")
xmap_buffer = iconfig.get("XMAP")["BUFFER"]

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

    else:
        logger.info(f"Called from {caller_name}")

    
    yield from bps.sleep(1)
        







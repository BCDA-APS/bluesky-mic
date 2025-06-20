"""
Creating a step scan plans that uses 1 scan record and drives more than
one positioners.

@author: yluo(grace227)

"""

__all__ = """
    step2d_random_pos
""".split()

import logging
import numpy as np
from apsbits.utils.controls_setup import oregistry
from apsbits.utils.config_loaders import get_config
from mic_common.utils.scan_monitor import execute_scan_1d
from isn.plans.utils.trajectory import generate_random_points
from isn.plans.utils.det_setup import xrf_me7_setup, ptycho_setup
import bluesky.plan_stubs as bps
from epics import caput

logger = logging.getLogger(__name__)
logger.info(__file__)

scan1 = oregistry["scan1"]
samx = oregistry["samx"]
samy = oregistry["samy"]
savedata = oregistry["savedata"]
shutter_open = oregistry["shutter_open"]
shutter_close = oregistry["shutter_close"]
shutter_open_status = oregistry["shutter_open_status"]
ptycho = oregistry["ptycho"]
ptycho_hdf = oregistry["ptycho_hdf"]
xrf_me7 = oregistry["xrf_me7"]
xrf_me7_hdf = oregistry["xrf_me7_hdf"]

iconfig = get_config()
netcdf_delimiter = iconfig.get("FILE_DELIMITER")
xrf_me7_folder = iconfig.get("XRF_ME7_FOLDER")
ptycho_folder = iconfig.get("PTYCHO_FOLDER")


def step2d_random_pos(
    samplename="smp1",
    user_comments="",
    scan_traj="spiral",
    width=0,
    height=0,
    x_center=None,
    y_center=None,
    stepsize_x=0,
    stepsize_y=0,
    dr = 0.2,
    nth = 3,
    dwell=0,
    ptycho_on=False,
    xrf_me7_on=False,
    ptycho_exp_factor=1,
):
    """
    Step 2D random position scan plan. This plan will drive samx and samy
    to random positions within the width and height of the scan. This plan
    will also use EPICS scanrecord. 

    The plan will drive samx and samy to the requested x_center and y_center, 
    and then perform a relative scan in the x and y directions.

    Parameters
    ----------
    samplename: 
        Str: The name of the sample
    user_comments: 
        Str: The user comments for the scan
    scan_traj: 
        Str: The trajectory of the scan. Options are "spiral" and "grid".
    width: 
        Float: The width of the scan
    height: 
        Float: The height of the scan
    x_center: 
        Float: The center of the scan. If not provided, 
        the plan assumes it's a relative scan mode
    y_center: 
        Float: The center of the scan. If not provided, 
        the plan assumes it's a relative scan mode
    stepsize_x: 
        Float: The step size of the scan in the x direction
    stepsize_y: 
        Float: The step size of the scan in the y direction
    dr: 
        Float: The delta radius of the scan
    nth: 
        Int: The number of theta steps of the scan
    dwell: 
        Float: The dwell time of the scan
    ptycho_on: 
        Bool: Whether to turn on the ptycho
    xrf_me7_on: 
        Bool: Whether to turn on the xrf me7
    """

    # """Open the shutter"""
    # logger.info("Opening the shutter")
    # yield from bps.mv(shutter_open, 1)
    # shutter_status = shutter_open_status.value  # when open, the status becomes 0
    # while shutter_status:
    #     shutter_status = shutter_open_status.value
    #     yield from bps.sleep(0.2)

    """Move to the requested x- and y- centers"""
    logger.info("Moving to the requested x- and y- centers")
    if x_center is not None:
        yield from bps.mv(samx, x_center)
    if y_center is not None:
        yield from bps.mv(samy, y_center)

    """Generate the scan trajectory"""
    samx_points, samy_points = generate_random_points(scan_traj, 0, 0, 
                                                      width, height, stepsize_x, stepsize_y, dr, nth)
    logger.info(f"Generated array of {samx_points.shape[0]} points")

    """Configure the scanrecord and pass the scan trajectory"""
    yield from scan1.set_scan_mode("table")
    yield from bps.mv(scan1.positioners.p2.mode, "table".upper())
    logger.info(f"Setting number of points to {samx_points.shape[0]}")
    yield from bps.mv(scan1.number_points, samx_points.shape[0])

    yield from bps.mv(scan1.positioners.p1.setpoint_pv, samx.prefix+'.VAL',
                      scan1.positioners.p1.readback_pv, samx.prefix+'.RBV')
    yield from bps.mv(scan1.positioners.p1.abs_rel, "relative".upper())
    yield from bps.mv(scan1.positioners.p2.setpoint_pv, samy.prefix+'.VAL',
                      scan1.positioners.p2.readback_pv, samy.prefix+'.RBV')
    yield from bps.mv(scan1.positioners.p2.abs_rel, "relative".upper())    
    caput(scan1.P1PA.pvname, samx_points)
    caput(scan1.P2PA.pvname, samy_points)
    
    # yield from bps.mv(scan1.positioner_delay, 0.1)
    yield from bps.sleep(0.1)

    """Configure the detectors"""
    num_capture = samx_points.shape[0]
    savedata.update_next_file_name()
    filename = savedata.next_file_name.replace(".mda", "")
        
    if xrf_me7_on and xrf_me7.connected and xrf_me7_hdf.connected:
        yield from xrf_me7_setup(num_capture, dwell, filename)

    elif ptycho_on and ptycho.connected and ptycho_hdf.connected:
        trigger_mode = "Internal Series"
        yield from ptycho_setup(trigger_mode, num_capture, dwell, 
                                ptycho_exp_factor, filename)

    """Generate the scan master file"""

    """Start executing scan"""
    savedata.update_next_file_name()
    yield from execute_scan_1d(scan1, scan_name=savedata.next_file_name)

    # """Close the shutter"""
    # yield from bps.mv(shutter_close, 1)

    """Reset the scan record to default"""
    yield from bps.sleep(1)
    yield from scan1.set_scan_mode("linear")
    yield from bps.mv(scan1.positioners.p2.mode, "linear".upper())
    yield from bps.mv(scan1.positioners.p2.setpoint_pv, '',
                      scan1.positioners.p2.readback_pv, '')

    """Disable manual trigger of eiger"""
    if ptycho_on and ptycho.connected:
        yield from ptycho.set_manual_trigger("Disable")



                
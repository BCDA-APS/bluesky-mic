"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    step2d
""".split()

import logging

from apsbits.utils.controls_setup import oregistry
from bluesky import plan_stubs as bps
from mic_common.utils.scan_monitor import execute_scan_2d

from .generallized_scan_1d import generalized_scan_1d

logger = logging.getLogger(__name__)
logger.info(__file__)

samx = oregistry["samx"]
samy = oregistry["samy"]
savedata = oregistry["savedata"]
scan1 = oregistry["scan1"]
scan2 = oregistry["scan2"]

scanmode = "LINEAR"


def step2d(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
    height=0,
    y_center=None,
    stepsize_y=0,
    dwell=0,
    smp_theta=None,
    xrf_on=True,
    ptycho_on=False,
    preamp_on=False,
    position_stream=False,
    wf_run=False,
    analysisMachine="mona2",
):
    """2D Bluesky plan that drives the x- and y- sample motors in stepping mode using
    ScanRecord

    The plan will drive samx and samy to the requested x_center and y_center,
    and then perform a relative scan in the x and y directions.

    Parameters
    ----------
    samplename:
        Str: The name of the sample
    user_comments:
        Str: The user comments for the scan
    width:
        Float: The width of the scan
    x_center:
        Float: The center of the scan in the x direction. Default is None which uses the current position of samx
    stepsize_x:
        Float: The step size in the x direction
    height:
        Float: The height of the scan
    y_center:
        Float: The center of the scan in the y direction. Default is None which uses the current position of samy
    stepsize_y:
        Float: The step size in the y direction
    dwell:
        Float: The dwell time in the scan
    smp_theta:
        Float: The theta of the sample
    xrf_on:
        Bool: Whether to collect XRF data
    ptycho_on:
        Bool: Whether to collect Ptycho data
    preamp_on:
        Bool: Whether to collect Preamp data
    position_stream:
        Bool: Whether to collect position stream data
    wf_run:
        Bool: Whether to run the workflow
    analysisMachine:
        Str: The name of the analysis machine
    """

    ##TODO Close shutter while setting up scan parameters

    """Move to the requested x- and y- centers"""
    logger.info("Moving to the requested x- and y- centers")
    if x_center is not None:
        yield from bps.mv(samx, x_center)
    if y_center is not None:
        yield from bps.mv(samy, y_center)

    """Set up the inner loop scan record based on the scan types and parameters"""
    yield from bps.mv(scan1.positioners.p1.abs_rel, "relative".upper())
    yield from generalized_scan_1d(
        scan1,
        samx,
        scanmode=scanmode,
        x_center=0,
        width=width,
        stepsize_x=stepsize_x,
        dwell=dwell,
    )

    """Set up the outter loop scan record"""
    yield from scan2.set_scan_mode(scanmode)
    yield from bps.mv(scan2.positioners.p1.abs_rel, "relative".upper())
    yield from generalized_scan_1d(
        scan2,
        samy,
        scanmode=scanmode,
        x_center=0,
        width=height,
        stepsize_x=stepsize_y,
        dwell=dwell,
    )

    """Start executing scan"""
    savedata.update_next_file_name()
    yield from execute_scan_2d(scan1, scan2, scan_name=savedata.next_file_name)

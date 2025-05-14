"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    dummy_testing
""".split()

import logging
import os

import bluesky.plan_stubs as bps
from apstools.devices import DM_WorkflowConnector

from ..configs.device_config import samx
from ..configs.device_config import savedata
from ..configs.device_config import scan1
from ..devices.data_management import api
from ..utils.dm_utils import dm_upload_wait
from ..utils.scan_monitor import execute_scan_1d
from .dm_plans import dm_submit_workflow_job
from .generallized_scan_1d import generalized_scan_1d
from .workflow_plan import run_workflow

logger = logging.getLogger(__name__)
logger.info(__file__)


def dummy_testing(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
    dwell=0,
    smp_theta=None,
    simdet_on=False,
    xrf_on=True,
    ptycho_on=False,
    preamp_on=False,
    fpga_on=False,
    position_stream=False,
    wf_run=False,
    analysisMachine="mona2",
):
    """Bluesky plan for testing but not moving any actual hardware
    
    Parameters  
    ----------
    samplename : 
        Str: The name of the sample.
    user_comments : 
        Str: The user comments for the scan.
    width : 
        Float: The width of the scan.
    x_center : 
        Float: The center of the scan in the x-direction.
    stepsize_x : 
        Float: The stepsize of the scan in the x-direction.
    dwell : 
        Float: The dwell time of the scan.
    smp_theta : 
        Float: The sample theta angle.
    simdet_on : 
        Bool: Whether to run Simdet.
    xrf_on : 
        Bool: Whether to run XRF.
    ptycho_on : 
        Bool: Whether to run Ptycho.
    preamp_on : 
        Bool: Whether to run Preamp.
    fpga_on : 
        Bool: Whether to run FPGA.
    position_stream : 
        Bool: Whether to run Position Stream.
    wf_run : 
        Bool: Whether to run DM workflow.
    analysisMachine : 
        Str: The analysis machine to use.
    """

    """Print out the input parameters"""
    for key, value in locals().items():
        logger.info(f"{key}: {value}")

    for i in range(stepsize_x):
        prog = round(i / stepsize_x * 100, 2)
        msg = "{"
        msg += f"Filename: 2xfm_0001.mda, Scan_progress: {prog}%, "
        msg += f"Line: 1/1, Scan_remaining: {(stepsize_x-i)*dwell}, "
        msg += f"Scanned {i}/{stepsize_x}"
        msg += "}"
        logger.info(msg)
        # logger.info(f"Scan progress: dummy_test: {prog}% :, scanned {i}/{stepsize_x}")
        yield from bps.sleep(dwell)

    logger.info("end of plan")

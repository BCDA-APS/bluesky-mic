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
from .generallized_scan_1d import generalized_scan_1d
from ..utils.scan_monitor import execute_scan_1d
from .workflow_plan import run_workflow
from ..utils.dm_utils import dm_upload_wait
from ..devices.data_management import api
from apstools.devices import DM_WorkflowConnector
from .dm_plans import dm_submit_workflow_job
from ..configs.device_config_19id import scan1, samx, savedata


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
    xrf_me7_on=True,
    ptycho_on=False,
    preamp_on=False,
    fpga_on=False,
    position_stream=False,
    wf_run=False,
    analysisMachine="mona2",
    eta=0,
):
    """Bluesky plan for testing but not moving any actual hardware"""

    for i in range(stepsize_x):
        prog = round(i / stepsize_x * 100, 2)
        logger.info(f"Scan progress: dummy_test: {prog}% :, scanned {i}/{stepsize_x}")
        yield from bps.sleep(dwell)

    logger.info("end of plan")

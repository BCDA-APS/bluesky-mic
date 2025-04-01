"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)

EXAMPLE::

    # Load this code in IPython or Jupyter notebook:
    %run -i user/fly2d_2idsft.py

    # # Run the plan with the RunEngine:
    # RE(scan_record2(scanrecord_name = 'scan1', ioc = "2idsft:", m1_name = 'm1',
    #                m1_start = -0.5, m1_finish = 0.5,
    #                m2_name = 'm3', m2_start = -0.2 ,m2_finish = 0.2, 
    #                npts = 50, dwell_time = 0.1))

"""

__all__ = """
    run_dm_analysis
""".split()

import logging
import os
import bluesky.plan_stubs as bps
from .dm_plans import dm_submit_workflow_job
from ..configs.device_config import xrf_dm_args, ptychoxrf_dm_args, ptychodus_dm_args
from ...mic_instrument.plans.workflow_plan import run_workflow
from ..devices.data_management import api
from apstools.devices import DM_WorkflowConnector

logger = logging.getLogger(__name__)
logger.info(__file__)


def run_dm_analysis(
    samplename="sample1",
    filePath="003003.h5",
    workflow="xrf-maps",
    experimentName="s19iddm_ptycho_xrf_test",
    dataDir="sample1/xspress3",
    detectors=3,
    analysisMahine="mona2",
):

    dm_workflow = DM_WorkflowConnector(name=samplename, labels=("dm",))

    if workflow == "xrf-maps":
        argsDict = xrf_dm_args.copy()
    if workflow == "ptychodus":
        argsDict = ptychodus_dm_args.copy()
    if workflow == "ptycho-xrf":
        argsDict = ptychoxrf_dm_args.copy()

    ##TODO Modify argsDict accordingly based on the scan parameters

    for k, v in locals().items():
        argsDict[k] = v

    yield from bps.sleep(1)
    yield from dm_submit_workflow_job(workflow, argsDict)
    logger.info(f"{len(api.listProcessingJobs())=!r}")
    logger.info("DM workflow Finished!")
    logger.info("end of plan")

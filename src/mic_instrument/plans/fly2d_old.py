"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    fly2d
""".split()

import logging
import os
from .generallized_scan_1d import generalized_scan_1d
from ..utils.scan_monitor import execute_scan_2d
from ...mic_instrument.plans.workflow_plan import run_workflow
from ..utils.dm_utils import dm_upload_wait
from ..devices.data_management import api
from apstools.devices import DM_WorkflowConnector
from .dm_plans import dm_submit_workflow_job
from ..configs.device_config import fscan1, fscanh, fscanh_samx, samy, savedata


logger = logging.getLogger(__name__)
logger.info(__file__)


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
    smp_theta=None,
    simdet_on=False,
    xrf_on=True,
    ptycho_on=False,
    preamp_on=False,
    fpga_on=False,
    position_stream=False,
    wf_run=False,
    analysisMachine="mona2",
    eta=0,
):
    """2D Bluesky plan that drives the x- and y- sample motors in fly mode using ScanRecord"""

    ##TODO Close shutter while setting up scan parameters

    """Set up scan record based on the scan types and parameters"""
    yield from generalized_scan_1d(fscanh, fscanh_samx, scanmode="FLY", **locals())
    yield from fscanh.set_positioner_drive(f"{fscanh_samx.pvname}")
    yield from fscanh.set_positioner_readback("")

    """Set up the outter loop scan record"""
    yield from fscan1.set_scan_mode("linear")
    yield from fscan1.set_positioner_drive(f"{samy.prefix}.VAL")
    yield from fscan1.set_positioner_readback(f"{samy.prefix}.RBV")
    yield from fscan1.set_center_width_stepsize(y_center, height, stepsize_y)

    """Start executing scan"""
    savedata.update_next_file_name()
    yield from execute_scan_2d(fscanh, fscan1, scan_name=savedata.next_file_name, 
                               print_outter_msg=True)

    #     #############################
    #     # START THE APS DM WORKFLOW #
    #     #############################

    #     if wf_run:
    #         dm_workflow = DM_WorkflowConnector(name=samplename, labels=("dm",))

    #         if all([xrf_me7_on, ptycho_on]):
    #             WORKFLOW = "ptycho-xrf"
    #             argsDict = ptychoxrf_dm_args.copy()
    #         elif xrf_me7_on:
    #             WORKFLOW = "xrf-maps"
    #             argsDict = xrf_dm_args.copy()
    #         else:
    #             WORKFLOW = "ptychodus"
    #             argsDict = ptychodus_dm_args.copy()

    #         ##TODO Modify argsDict accordingly based on the scan parameters
    #         argsDict['analysisMachine'] = analysisMachine

    #         yield from dm_submit_workflow_job(WORKFLOW, argsDict)
    #         logger.info(f"{len(api.listProcessingJobs())=!r}")
    #         logger.info("DM workflow Finished!")

    #     logger.info("end of plan")

    # else:
    #     logger.info(f"Having issue connecting to scan record: {scan1.prefix}")

    # # yield from bps.sleep(1)
    # # print("end of plan")

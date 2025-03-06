"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    step1d
""".split()

import logging
import os
from .generallized_scan_1d import generalized_scan_1d
from ..utils.scan_monitor import execute_scan_1d
from .workflow_plan import run_workflow
from ..utils.dm_utils import dm_upload_wait
from ..devices.data_management import api
from apstools.devices import DM_WorkflowConnector
from .dm_plans import dm_submit_workflow_job
from ..configs.device_config import scan1, samx, savedata
from mic_instrument.plans.helper_funcs import selected_dets, calculate_num_capture, move_to_position


logger = logging.getLogger(__name__)
logger.info(__file__)


def step1d(
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
):
    """1D Bluesky plan that drives the a sample motor in stepping mode using ScanRecord
    
    Parameters
    ----------
    samplename:     
        Str: The name of the sample
    user_comments: 
        Str: The user comments for the scan
    width: 
        Float: The width of the scan
    x_center: 
        Float: The center of the scan
    stepsize_x: 
        Float: The step size of the scan
    dwell: float
        Float: The dwell time of the scan
    smp_theta: 
        Float: The sample theta angle
    simdet_on: 
        Bool: Whether to turn on the simdet
    xrf_me7_on: 
        Bool: Whether to turn on the xrf me7
    ptycho_on: 
        Bool: Whether to turn on the ptycho
    preamp_on: 
        Bool: Whether to turn on the preamp
    fpga_on: 
        Bool: Whether to turn on the fpga
    position_stream: 
        Bool: Whether to turn on the position stream
    wf_run: 
        Bool: Whether to run the dm workflow
    analysisMachine: 
        Str: The analysis machine to use
        
    """

    ##TODO Close shutter while setting up scan parameters

    """Set up scan record based on the scan types and parameters"""
    # yield from generalized_scan_1d(scan1, samx, scanmode="LINEAR", **locals())
    yield from generalized_scan_1d(scan1, samx, scanmode="LINEAR", x_center=x_center,
                                   width=width, stepsize_x=stepsize_x, dwell=dwell)

    """Check which detectors to trigger"""
    logger.info("Determining which detectors are selected")
    dets = selected_dets(**locals())
    
    """Generate master file"""
    master_file = generate_master_file(dets)

    """Start executing scan"""
    savedata.update_next_file_name()
    yield from execute_scan_1d(scan1, scan_name=savedata.next_file_name)

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

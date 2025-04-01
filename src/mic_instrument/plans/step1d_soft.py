"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    step1d
""".split()

import logging
import os
from pathlib import Path
from apstools.devices import DM_WorkflowConnector
from mic_instrument.devices.data_management import api
from mic_instrument.plans.generallized_scan_1d import generalized_scan_1d
from mic_instrument.plans.workflow_plan import run_workflow
from mic_instrument.plans.dm_plans import dm_submit_workflow_job
from mic_instrument.utils.scan_monitor import execute_scan_1d
from mic_instrument.utils.dm_utils import dm_upload_wait
from mic_instrument.utils.watch_pvs_write_hdf5 import write_scan_master_h5
from mic_instrument.configs.device_config import scan1, samx, savedata, master_file_yaml
from mic_instrument.plans.helper_funcs import selected_dets, calculate_num_capture, move_to_position

logger = logging.getLogger(__name__)
logger.info(__file__)


def step1d_soft(
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
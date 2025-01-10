"""
Creating a general scan 1D function that can be modify to perform either 
fly / step scans and also drive different positioners

@author: yluo(grace227)

"""

__all__ = """
    generalized_scan_1d
""".split()

import logging
import os
from ..utils.scan_monitor import execute_scan
import bluesky.plan_stubs as bps
from apstools.plans import run_blocking_function
from .dm_plans import dm_submit_workflow_job
from ophyd.status import Status
from ..configs.device_config_19id import (
    scan1,
    savedata,
    xrf_me7,
    xrf_me7_hdf,
    xrf_dm_args,
    ptychoxrf_dm_args,
    ptychodus_dm_args,
)
from .workflow_plan import run_workflow
from ..utils.dm_utils import dm_upload_wait
from ..devices.data_management import api
from apstools.devices import DM_WorkflowConnector


logger = logging.getLogger(__name__)
logger.info(__file__)

SCAN_OVERHEAD = 0.3
det_name_mapping = {
    "simdet": {"cam": None, "hdf": None},
    "xrf_me7": {"cam": xrf_me7, "hdf": xrf_me7_hdf},
    "preamp": {"cam": None, "hdf": None},
    "fpga": {"cam": None, "hdf": None},
    "ptycho": {"cam": None, "hdf": None},
}


def selected_dets(kwargs):
    dets = {}
    rm_str = "_on"
    for k, v in kwargs.items():
        if all([v, isinstance(v, bool), rm_str in k]):
            det_str = k[: -len(rm_str)]
            dets.update({det_str: det_name_mapping[det_str]})
    #         dets.append(det_name_mapping[det_str])
    return dets


# def detectors_init(dets: list):
#     for d in dets:
#         logger.info(f"Initializing detector {d.name}")
#         yield from d.initialize()


# def detectors_setup(dets: list, dwell=0, num_frames=0):
#     for d in dets:
#         logger.info(
#             f"Assigning detector {d.name} to have dwell time \
#                 of {dwell} and # frames of {num_frames}"
#         )


def generalized_scan_1d(scanrecord, positioner, scanmode="LINEAR", exec_plan=False, **kwargs):
    logger.info(f"Using {scanrecord.prefix} as the scanRecord")
    logger.info(f"Using {positioner.prefix} as the motor")
    if scanrecord.connected and positioner.connected:
        logger.info(f"{scanrecord.prefix} is connected")
        logger.info(f"{positioner.prefix} is connected")

        """Set up scan mode to be FLY """
        yield from scanrecord.set_scan_mode(scanmode)

        """Assign the desired positioner in scanrecord """
        yield from scanrecord.set_positioner_drive(f"{positioner.prefix}.VAL")
        yield from scanrecord.set_positioner_readback(f"{positioner.prefix}.RBV")

        """Set up scan parameters and get estimated time of a scan"""
        yield from scanrecord.set_center_width_stepsize(kwargs["x_center"], kwargs["width"], kwargs["stepsize_x"])
        numpts_x = scanrecord.number_points.value
        eta = numpts_x * kwargs["dwell"] * (1 + SCAN_OVERHEAD)
        logger.info(f"Number_points in X: {numpts_x}")
        logger.info(f"Estimated_time for this scan is {eta}")

        """Check which detectors to trigger"""
        logger.info("Determining which detectors are selected")
        dets = selected_dets(kwargs)

        """Create folder for the desire file/data structure"""
        basepath = savedata.get().file_system
        for det_name, det_var in dets.items():
            det_path = os.path.join(basepath, det_name)
            logger.info(f"Setting up {det_name} to have data saved at {det_path}")
            hdf = det_var["hdf"]
            if hdf is not None:
                hdf.set_filepath(det_path)

    #     # ##TODO Based on the selected detector, setup DetTriggers in inner scanRecord
    #     # for i, d in enumerate(dets):
    #     #     cmd = f"yield from bps.mv(scan1.triggers.t{i}.trigger_pv, {d.Acquire.pvname}"
    #     #     eval(cmd)

    #     ##TODO Assign the proper data path to the detector IOCs

        """Start executing scan"""
        if exec_plan:
            yield from execute_scan(scanrecord, scanrecord.number_points.value)

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

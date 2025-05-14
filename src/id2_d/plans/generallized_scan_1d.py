"""
Creating a general scan 1D function that can be modify to perform either
fly / step scans and also drive different positioners

@author: yluo(grace227)

"""

__all__ = """
    generalized_scan_1d
""".split()

import logging

from mic_instrument.configs.device_config import savedata
from mic_instrument.configs.device_config import scan_overhead
from mic_instrument.utils.scan_monitor import execute_scan_1d

# from mic_instrument.plans.dm_plans import dm_submit_workflow_job
# from .workflow_plan import run_workflow
# from .before_after_fly import before_flyscan, setup_inner_flyscan_xrf_triggers, calculate_num_capture
# from ..utils.dm_utils import dm_upload_wait
# from ..devices.data_management import api
# from apstools.devices import DM_WorkflowConnector
# import bluesky.plan_stubs as bps
# import os


logger = logging.getLogger(__name__)
logger.info(__file__)


def generalized_scan_1d(
    scanrecord,
    positioner,
    scanmode="LINEAR",
    x_center=None,
    width=0,
    stepsize_x=0,
    dwell=0,
    exec_plan=False,
):
    """
    Generalized scan 1D function that can be modify to perform either
    fly / step scans and also drive different positioners
    """

    logger.info(f"Using {scanrecord.prefix} as the scanRecord")
    logger.info(f"Using {positioner} as the motor")
    if scanrecord.connected and positioner.connected:
        logger.info(f"{scanrecord.prefix} is connected")
        logger.info(f"{positioner} is connected")

        """Set up scan mode to be either FLY or STEP """
        yield from scanrecord.set_scan_mode(scanmode)

        """Assign the desired positioner in scanrecord """
        try:
            yield from scanrecord.set_positioner_drive(f"{positioner.prefix}.VAL")
            yield from scanrecord.set_positioner_readback(f"{positioner.prefix}.RBV")
        except Exception as e:
            logger.info(f"Fail to set positioner in {scanrecord.prefix} due to {e}")
            yield from scanrecord.set_positioner_drive(f"{positioner.pvname}")
            yield from scanrecord.set_positioner_readback(f"{positioner.pvname}")

        """Set up scan parameters and get estimated time of a scan"""
        yield from scanrecord.set_center_width_stepsize(x_center, width, stepsize_x)
        numpts_x = scanrecord.number_points.value
        eta = numpts_x * dwell * (1 + scan_overhead)
        logger.info(f"Number_points in X: {numpts_x}")
        logger.info(f"Estimated_time for this scan is {eta}")

        """Start executing scan"""
        if exec_plan:
            savedata.update_next_file_name()
            yield from execute_scan_1d(scanrecord, scan_name=savedata.next_file_name)

        # """Initialize detector with desired pts and exposure time """
        # for det_name, det_var in dets.items():
        #     cam = det_var["cam"]
        #     file_plugin = det_var["file_plugin"]

        #     if det_name == "xrf":
        #         if scanmode == "LINEAR":
        #             yield from cam.stepscan_before()
        #             yield from bps.mv(stepdwell, kwargs["dwell"])
        #         elif sis3820.connected:
        #             # Set up triggers for FLY scans, sis3820 will be sending out pulses. The number of pulses is numpts_x - 2
        #             num_pulses = numpts_x - 2
        #             yield from setup_inner_flyscan_triggers(scanrecord, xrf, xrf_netcdf, sis3820, num_pulses)

        #             # Set up the detector for flyscan
        #             yield from cam.flyscan_before(num_pulses)

        #             # Set up the file writer for the detector
        #             num_capture = calculate_num_capture(numpts_x)
        #             yield from file_plugin.setup_file_writer(savedata, det_name, num_capture,
        #                                                     filename=next_file_name.replace(".mda", "_"),
        #                                                     beamline_delimiter=netcdf_delimiter)
        #             yield from file_plugin.set_capture("capturing")

        #     elif det_name == "ptycho":
        #         if scanmode == "LINEAR":
        #             print("Change the trigger in the outter scanrecord")
        #         elif sis3820.connected:
        #             print("Set up detector and struck card in the outter scanrecord")

        # if cam is not None:
        #     # try:
        #         # yield from cam.scan_init(exposure_time=kwargs["dwell"], num_images=numpts_x)
        #     if det_name == "xrf" and scanmode == "LINEAR":
        #         yield from cam.stepscan_before()
        #         yield from bps.mv(stepdwell, kwargs["dwell"])
        #     elif det_name == "xrf" and scanmode == "FLY":
        #         yield from before_flyscan(scanrecord.start_position.get(),
        #                                     scanrecord.stepsize.get(),
        #                                     numpts_x, dets, kwargs["dwell"],
        #                                     savedata=savedata,
        #                                     filename=next_file_name,
        #                                     beamline_delimiter=netcdf_delimiter)
        #     elif det_name == "ptycho" and scanmode == "FLY":
        #         yield from before_flyscan(scanrecord.start_position.get(),
        #                                     scanrecord.stepsize.get(),
        #                                     numpts_x, dets, kwargs["dwell"],
        #                                     ptycho_exp_factor=kwargs["ptycho_exp_factor"],
        #                                     savedata=savedata,
        #                                     filename=next_file_name,
        #                                     beamline_delimiter=netcdf_delimiter)

        #     # except Exception as e:
        #     #     logger.error(f"Error occurs when setting up {cam.prefix}: {e}")

        # """Initialize detector file plugin"""
        # basepath = savedata.get().file_system
        # for det_name, det_var in dets.items():
        #     file_plugin = det_var["file_plugin"]
        #     if all([det_name == "xrf", scanmode == "FLY", file_plugin is not None]):
        #         det_path = os.path.join(basepath, det_name.upper())
        #         logger.info(f"Setting up {det_name} to have data saved at {det_path}")
        #         if not os.path.exists(det_path):
        #             os.makedirs(det_path, exist_ok=True)
        #             logger.info(f"Directory '{det_path}' created for {det_name}.")

        #         newpath = file_plugin.sync_file_path(det_path, netcdf_delimiter)
        #         yield from file_plugin.set_filepath(newpath)
        #         if file_plugin.file_path_exists.get():
        #             logger.info(f"File path is set to {file_plugin.file_path.get()}")
        #         else:
        #             logger.error(f"File path {file_plugin.file_path.get()} does not exist")
        #     # if file_plugin is not None:
        #     #     yield from file_plugin.initialize()

        # """Create folder for the desire file/data structure"""
        # basepath = savedata.get().file_system
        # basename = savedata.get().base_name
        # next_scan_number = savedata.get().next_scan_number
        # for det_name, det_var in dets.items():
        #     det_path = os.path.join(basepath, det_name)
        #     logger.info(f"Setting up {det_name} to have data saved at {det_path}")
        #     file_plugin = det_var["file_plugin"]
        #     if file_plugin is not None:
        #         try:
        #             yield from file_plugin.set_filepath(det_path)
        #             yield from file_plugin.set_filename(basename)
        #             yield from file_plugin.set_filenumber(next_scan_number)
        #         except Exception as e:
        #             logger.error(f"Error occurs when setting up {savedata.prefix}: {e}")

        # #     # ##TODO Based on the selected detector, setup DetTriggers in inner scanRecord
        # #     # for i, d in enumerate(dets):
        # #     #     cmd = f"yield from bps.mv(scan1.triggers.t{i}.trigger_pv, {d.Acquire.pvname}"
        # #     #     eval(cmd)

        # #     ##TODO Assign the proper data path to the detector IOCs

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

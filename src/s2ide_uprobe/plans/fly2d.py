"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    fly2d
""".split()

import logging

import bluesky.plan_stubs as bps
from mic_instrument.configs.device_config import fscan1
from mic_instrument.configs.device_config import fscanh
from mic_instrument.configs.device_config import fscanh_dwell
from mic_instrument.configs.device_config import fscanh_samx
from mic_instrument.configs.device_config import netcdf_delimiter
from mic_instrument.configs.device_config import samy
from mic_instrument.configs.device_config import savedata
from mic_instrument.configs.device_config import sis3820
from mic_instrument.plans.before_after_fly import setup_flyscan_ptycho_triggers
from mic_instrument.plans.generallized_scan_1d import generalized_scan_1d
from mic_instrument.plans.helper_funcs import selected_dets

from ..utils.scan_monitor import execute_scan_2d

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
    xrf_on=True,
    ptycho_on=False,
    preamp_on=False,
    fpga_on=False,
    position_stream=False,
    wf_run=False,
    analysisMachine="mona2",
    eta=0,
    ptycho_exp_factor=3,
):
    """2D Bluesky plan that drives the x- and y- sample motors in fly mode using ScanRecord"""

    ##TODO Close shutter while setting up scan parameters

    """Set up scan record based on the scan types and parameters"""
    yield from generalized_scan_1d(
        fscanh,
        fscanh_samx,
        scanmode="FLY",
        x_center=x_center,
        width=width,
        stepsize_x=stepsize_x,
        dwell=dwell,
    )
    yield from fscanh.set_positioner_drive(f"{fscanh_samx.pvname}")
    yield from fscanh.set_positioner_readback("")

    """Set up the outter loop scan record"""
    yield from fscan1.set_scan_mode("linear")
    yield from fscan1.set_positioner_drive(f"{samy.prefix}.VAL")
    yield from fscan1.set_positioner_readback(f"{samy.prefix}.RBV")

    # check if the scan movement is relative or absolute
    scan_movement = fscan1.scan_movement.enum_strs[fscan1.scan_movement.get()]
    if scan_movement == "RELATIVE":
        yield from bps.mv(samy, y_center)
        yield from fscan1.set_center_width_stepsize(0, height, stepsize_y)
    else:
        yield from fscan1.set_center_width_stepsize(y_center, height, stepsize_y)

    """Assign the per-pixel dwell time"""
    logger.info(f"Setting per-pixel dwell time ({fscanh_dwell.pvname}) to {dwell} ms")
    yield from bps.mv(fscanh_dwell, dwell)

    """Check which detectors to trigger"""
    logger.info("Determining which detectors are selected")
    dets = selected_dets(**locals())

    """Update the next file name for the detector file plugin"""
    savedata.update_next_file_name()
    next_file_name = savedata.next_file_name

    """Initialize detectors with desired pts, exposure time and file writer """
    if sis3820.connected:
        # Set up triggers for FLY scans, sis3820 will be sending out pulses. The number of pulses is numpts_x - 2
        numpts_x = fscanh.number_points.value
        num_pulses = numpts_x - 2
        for det_name, det_var in dets.items():
            cam = det_var["cam"]
            file_plugin = det_var["file_plugin"]
            filename = next_file_name.replace(".mda", "_")

            # TODO: We need to update filename in xrf file plugin, Assuming the XRF detector is handled by usercalc already
            # if det_name == "xrf":
            #     num_capture = calculate_num_capture(numpts_x)
            #     yield from setup_flyscan_XRF_triggers(
            #         fscanh, cam, file_plugin, sis3820, num_pulses
            #     )
            #     yield from cam.flyscan_before(num_pulses)
            #     yield from file_plugin.setup_file_writer(
            #         savedata,
            #         det_name,
            #         num_capture,
            #         filename=filename,
            #         beamline_delimiter=netcdf_delimiter,
            #     )
            #     yield from file_plugin.set_capture("capturing")

            if det_name == "ptycho":
                yield from setup_flyscan_ptycho_triggers(
                    fscan1, fscanh, cam, eiger_filewriter=file_plugin
                )
                yield from cam.scan_init(dwell / 1e3, num_pulses, ptycho_exp_factor)

                if file_plugin is not None:
                    # If an hdf5 file plugin is used, we need to disable the Eiger's default file writer.
                    yield from cam.set_file_writer_enable("Disable")

                    next_file_number_str = str(savedata.next_scan_number.get()).zfill(3)
                    eiger_filename = f"fly{next_file_number_str}_data"
                    yield from file_plugin.setup_file_writer(
                        savedata,
                        det_name,
                        num_pulses,
                        filename=eiger_filename,
                        beamline_delimiter=netcdf_delimiter,
                    )
                # yield from setup_eiger_filewriter(
                #     cam,
                #     file_plugin,
                #     savedata,
                #     det_name,
                #     num_pulses,
                #     filename,
                #     netcdf_delimiter,
                # )

    """Start executing scan"""

    # yield from bps.sleep(1)
    yield from execute_scan_2d(
        fscanh, fscan1, scan_name=savedata.next_file_name, print_outter_msg=True
    )

    # Restore the previous scan record triggers
    logger.info("Restoring the previous scan record triggers before exiting the plan")
    yield from fscan1.restore_detTriggers()
    yield from fscanh.restore_detTriggers()

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

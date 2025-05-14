"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    fly2d
""".split()

import logging

import bluesky.plan_stubs as bps

from s19.configs.device_config import fscan1
from s19.configs.device_config import fscanh
from s19.configs.device_config import fscanh_dwell
from s19.configs.device_config import fscanh_samx
from s19.configs.device_config import netcdf_delimiter
from s19.configs.device_config import samy
from s19.configs.device_config import savedata
from s19.configs.device_config import sis3820
from s19.plans.before_after_fly import setup_eiger_filewriter
from s19.plans.before_after_fly import setup_flyscan_ptycho_triggers
from s19.plans.before_after_fly import setup_flyscan_XRF_triggers
from s19.plans.generallized_scan_1d import generalized_scan_1d
from s19.plans.helper_funcs import move_to_position
from s19.plans.helper_funcs import selected_dets
from s19.utils.scan_monitor import execute_scan_2d

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
    preamp1_on=False,
    preamp2_on=False,
    fpga_on=False,
    position_stream=False,
    wf_run=False,
    analysisMachine="mona2",
    ptycho_exp_factor=1,
):
    """
    2D Bluesky plan that drives the x- and y- sample motors in fly mode using
    ScanRecord.

    Parameters
    ----------
    samplename : str, optional
        Name of the sample, defaults to "smp1"
    user_comments : str, optional
        User comments for the scan
    width : float, optional
        Width of the scan in motor units
    x_center : float, optional
        Center position of the scan in x
    stepsize_x : float, optional
        Step size in x motor units
    height : float, optional
        Height of the scan in motor units
    y_center : float, optional
        Center position of the scan in y
    stepsize_y : float, optional
        Step size in y motor units
    dwell : float, optional
        Dwell time per point in seconds
    smp_theta : float, optional
        Sample theta angle
    xrf_on : bool, optional
        Enable XRF detector
    ptycho_on : bool, optional
        Enable ptychography detector
    preamp1_on : bool, optional
        Enable preamp1 detector
    preamp2_on : bool, optional
        Enable preamp2 detector
    fpga_on : bool, optional
        Enable FPGA detector
    position_stream : bool, optional
        Enable position streaming
    wf_run : bool, optional
        Enable workflow run
    analysisMachine : str, optional
        Analysis machine name, defaults to "mona2"
    ptycho_exp_factor : float, optional
        Exposure factor for ptychography
    """

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
    if fscan1.scan_movement.get(as_string=True) == "relative":
        yield from move_to_position(samy, y_center)

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
        # Set up triggers for FLY scans, sis3820 will be sending out pulses.
        # The number of pulses is numpts_x - 2
        numpts_x = fscanh.number_points.value
        num_pulses = numpts_x - 2
        filename = next_file_name.replace(".mda", "")
        if dets:
            for det_name, det_var in dets.items():
                cam = det_var["cam"]
                file_plugin = det_var["file_plugin"]
                savedata.update_next_file_name()

                if det_name == "xrf":
                    # When it's zero, the num_capture won't be overwritten
                    num_capture = 0
                    yield from setup_flyscan_XRF_triggers(
                        fscanh, cam, file_plugin, sis3820, num_pulses
                    )
                    yield from cam.flyscan_before(num_pulses)

                    yield from file_plugin.setup_file_writer(
                        savedata,
                        det_name,
                        num_capture,
                        filename=filename,
                        beamline_delimiter=netcdf_delimiter,
                    )
                    yield from file_plugin.set_capture("capturing")

                if det_name == "ptycho":
                    yield from setup_flyscan_ptycho_triggers(
                        fscan1, fscanh, cam, eiger_filewriter=file_plugin
                    )
                    yield from cam.flyscan_before(num_pulses, dwell, ptycho_exp_factor)
                    yield from setup_eiger_filewriter(
                        cam,
                        file_plugin,
                        savedata,
                        det_name,
                        num_pulses,
                        filename,
                        netcdf_delimiter,
                    )

                if any([det_name == "preamp1", det_name == "preamp2"]):
                    yield from file_plugin.setup_file_writer(
                        savedata,
                        det_name,
                        num_capture,
                        filename=filename,
                        beamline_delimiter=netcdf_delimiter,
                    )

    """Start executing scan"""
    yield from execute_scan_2d(
        fscanh,
        fscan1,
        scan_name=savedata.next_file_name,
        print_outter_msg=True,
    )

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

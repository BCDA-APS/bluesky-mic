"""
Creating a bluesky plan that waits for the desired incident mono energy before performing a 2D scan.

@author: yluo(grace227)


"""

__all__ = """
    xane_fly2d
""".split()

import logging

import bluesky.plan_stubs as bps
from apsbits.core.instrument_init import oregistry

from s2idd_uprobe.plans.fly2d import fly2d

kohzu = oregistry["kohzu_mono"]
# from mic_instrument.plans.generallized_scan_1d import generalized_scan_1d
# from mic_instrument.plans.before_after_fly import setup_flyscan_XRF_triggers
# from mic_instrument.utils.scan_monitor import execute_scan_2d
# from mic_instrument.configs.device_config import (
#     fscan1,
#     fscanh,
#     fscanh_samx,
#     samy,
#     savedata,
#     sis3820,
#     netcdf_delimiter,
#     fscanh_dwell,
#     kohzu,

# from mic_instrument.plans.helper_funcs import selected_dets
# from mic_instrument.plans.toggle_usercalc import disable_usercalc, enable_usercalc


logger = logging.getLogger(__name__)
logger.info(__file__)

det_foldername = {"xrf": "flyXRF", "preamp1": "tetramm", "preamp2": "tetramm2"}


def xane_fly2d(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
    height=0,
    y_center=None,
    stepsize_y=0,
    dwell=0,
    inc_eng=None,
    adjust_zp=False,
    xrf_on=True,
    preamp1_on=True,
    preamp2_on=False,
):
    """2D Bluesky plan that drives Kohzu and the x- and y- sample motors in fly mode using ScanRecord

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
    height :
        Float: The height of the scan.
    y_center :
        Float: The center of the scan in the y-direction.
    stepsize_y :
        Float: The stepsize of the scan in the y-direction.
    dwell :
        Float: The dwell time of the scan.
    inc_eng :
        Float: The incident energy of the scan.
    adjust_zp :
        Bool: Whether to adjust the zone plate position based on the incident energy.
    xrf_on :
        Bool: Whether to run XRF.
    preamp1_on :
        Bool: Whether to run Preamp1.
    preamp2_on :
        Bool: Whether to run Preamp2.

    """

    """Lets go to the desired incident energy"""
    yield from kohzu.set_energy(inc_eng)
    yield from kohzu.set_move(1)
    ready = False
    while not ready:
        logger.info(
            f"Waiting for Kohzu to be ready at {inc_eng} keV, "
            f"current energy: {kohzu.energy_rbv.get()} keV"
        )
        kohzu_status = kohzu.moving.get(as_string=True)
        if kohzu_status == "Done":
            ready = True
        yield from bps.sleep(0.1)

    """Perform the 2D scan"""
    yield from fly2d(
        samplename=samplename,
        user_comments=user_comments,
        width=width,
        x_center=x_center,
        stepsize_x=stepsize_x,
        height=height,
        y_center=y_center,
        stepsize_y=stepsize_y,
        dwell=dwell,
        xrf_on=xrf_on,
        preamp1_on=preamp1_on,
        preamp2_on=preamp2_on,
        inc_eng=inc_eng,
        adjust_zp=adjust_zp,
    )
    yield from bps.sleep(1)

    # """Disable the usercalc that used in scan record"""
    # yield from disable_usercalc()

    # """Set up scan record based on the scan types and parameters"""
    # yield from generalized_scan_1d(
    #     fscanh,
    #     fscanh_samx,
    #     scanmode="FLY",
    #     x_center=x_center,
    #     width=width,
    #     stepsize_x=stepsize_x,
    #     dwell=dwell,
    # )
    # yield from fscanh.set_positioner_drive(f"{fscanh_samx.pvname}")
    # yield from fscanh.set_positioner_readback("")

    # """Set up the outter loop scan record"""
    # yield from fscan1.set_scan_mode("linear")
    # yield from fscan1.set_positioner_drive(f"{samy.prefix}.VAL")
    # yield from fscan1.set_positioner_readback(f"{samy.prefix}.RBV")

    # # check if the scan movement is relative or absolute
    # scan_movement = fscan1.scan_movement.enum_strs[fscan1.scan_movement.get()]
    # if scan_movement == "RELATIVE":
    #     yield from bps.mv(samy, y_center)
    #     yield from fscan1.set_center_width_stepsize(0, height, stepsize_y)
    # else:
    #     yield from fscan1.set_center_width_stepsize(y_center, height, stepsize_y)

    # """Assign the per-pixel dwell time"""
    # logger.info(
    #     f"Setting per-pixel dwell time ({fscanh_dwell.pvname}) to {dwell} ms"
    # )
    # yield from bps.mv(fscanh_dwell, dwell)

    # """Check which detectors to trigger"""
    # logger.info("Determining which detectors are selected")
    # dets = selected_dets(**locals())

    # """Update the next file name for the detector file plugin"""
    # savedata.update_next_file_name()
    # next_file_name = savedata.next_file_name

    # """Generate scan_master.h5 file"""

    # """Initialize detectors with desired pts, exposure time and file writer """
    # if sis3820.connected:
    #     # Set up triggers for FLY scans, sis3820 will be sending out pulses. The number of pulses is numpts_x - 2
    #     numpts_x = fscanh.number_points.value
    #     num_pulses = numpts_x - 2
    #     filename = next_file_name.replace(".mda", "")
    #     if dets:
    #         for det_name, det_var in dets.items():
    #             cam = det_var["cam"]
    #             file_plugin = det_var["file_plugin"]
    #             savedata.update_next_file_name()

    #             if det_name == "xrf":
    #                 # num_capture = calculate_num_capture(numpts_x)
    #                 num_capture = 0 # When it's zero, the num_capture won't be overwritten
    #                 yield from setup_flyscan_XRF_triggers(
    #                     fscanh, cam, file_plugin, sis3820, num_pulses
    #                 )
    #                 yield from cam.flyscan_before(num_pulses)

    #                 yield from file_plugin.setup_file_writer(
    #                     savedata,
    #                     det_foldername[det_name],
    #                     num_capture,
    #                     filename=filename,
    #                     beamline_delimiter=netcdf_delimiter,
    #                 )
    #                 # yield from file_plugin.set_capture("capturing")

    #             elif any([det_name == "preamp1", det_name == "preamp2"]):
    #                 logger.info(f"Setting up file writer for {det_name}, {file_plugin.file_path.get()}")
    #                 yield from file_plugin.setup_file_writer(
    #                     savedata,
    #                     det_foldername[det_name],
    #                     num_capture,
    #                     filename=filename,
    #                     beamline_delimiter=netcdf_delimiter,
    #                 )

    #             yield from file_plugin.set_capture("capturing")

    # """Start executing scan"""

    # # yield from bps.sleep(1)
    # yield from execute_scan_2d(fscanh, fscan1, scan_name=savedata.next_file_name,
    #                            print_outter_msg=True)

    # """Enable the usercalc that used in scan record"""
    # yield from enable_usercalc()

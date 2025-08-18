"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    fly2d
""".split()

import logging

import bluesky.plan_stubs as bps
from apsbits.core.instrument_init import oregistry
from apsbits.utils.config_loaders import get_config
from mic_common.utils.scan_monitor import execute_scan_2d
from s2idd_uprobe.plans.before_after_fly import setup_flyscan_XRF_triggers
from mic_common.plans.generallized_scan_1d import generalized_scan_1d
from s2idd_uprobe.plans.helper_funcs import selected_dets
from s2idd_uprobe.plans.toggle_usercalc import disable_usercalc
from s2idd_uprobe.plans.toggle_usercalc import enable_usercalc

logger = logging.getLogger(__name__)

det_foldername = {"xrf": "flyXRF", "preamp1": "tetramm", "preamp2": "tetramm2"}

fscan1 = oregistry["fscan1"]
fscanh = oregistry["fscanh"]
fscanh_dwell = oregistry["fscanh_dwell"]
fscanh_samx = oregistry["fscanh_samx"]
# netcdf_delimiter = oregistry["netcdf_delimiter"]
samx = oregistry["samx"]
samy = oregistry["samy"]
samz = oregistry["samz"]
savedata = oregistry["savedata"]
sis3820 = oregistry["sis3820"]
xrf = oregistry["xrf"]
xrf_netcdf = oregistry["xrf_netcdf"]
preamp1_netcdf = oregistry["tetramm1_netcdf"]
iconfig = get_config()
scan_overhead = iconfig.get("SCAN_OVERHEAD")
netcdf_delimiter = iconfig.get("FILE_DELIMITER")
xmap_buffer = iconfig.get("XMAP", "BUFFER")


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
    sample_z=None,
    inc_eng=None,
    adjust_zp=False,
    xrf_on=True,
    preamp1_on=False,
    preamp2_on=False,
):
    """2D Bluesky plan that drives the x- and y- sample motors in fly mode using ScanRecord

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
    sample_z :
        Float: The z position of the sample.
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

    # """Disable the usercalc that used in scan record"""
    # yield from disable_usercalc()

    """Move the sample to the requested z position"""
    if sample_z is not None:
        yield from bps.mv(samz, sample_z)
    """Move to the requested x- and y- centers"""
    if x_center is not None:
        yield from bps.mv(samx, x_center)
    if y_center is not None:
        yield from bps.mv(samy, y_center)

    """Set up inner scan record based on the scan types and parameters"""
    yield from generalized_scan_1d(fscanh, fscanh_samx, savedata, scan_overhead=scan_overhead,
                                scanmode="FLY", x_center=x_center, width=width, 
                                stepsize_x=stepsize_x, dwell=dwell)
    yield from fscanh.set_positioner_readback("")

    """Set up the outter loop scan record"""
    yield from bps.mv(fscan1.positioners.p1.abs_rel, "relative".upper())
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

    # """Check which detectors to trigger"""
    # logger.info("Determining which detectors are selected")
    # dets = selected_dets(**locals())

    """Update the next file name for the detector file plugin"""
    savedata.update_next_file_name()
    next_file_name = savedata.next_file_name

    # """Generate scan_master.h5 file"""

    """Initialize detectors with desired pts, exposure time and file writer """
    if sis3820.connected:
        # Set up triggers for FLY scans, sis3820 will be sending out pulses. The number of pulses is numpts_x - 2
        numpts_x = fscanh.number_points.value
        num_pulses = numpts_x - 2
        filename = next_file_name.replace(".mda", "")

        if all([xrf_on, xrf.connected, xrf_netcdf.connected]):
            num_capture = 0 # When it's zero, the num_capture won't be overwritten
            yield from setup_flyscan_XRF_triggers(
                fscanh, xrf, xrf_netcdf, sis3820, num_pulses
            )
            yield from xrf.flyscan_before(num_pulses)
            
            yield from xrf_netcdf.setup_file_writer(
                savedata,
                det_foldername["xrf"],
                num_capture,
                filename=filename,
                beamline_delimiter=netcdf_delimiter,
            )

            yield from xrf_netcdf.set_capture("capturing")

        if all([preamp1_on, preamp1_netcdf.connected]):
            logger.info(f"Setting up file writer for preamp1, {preamp1_netcdf.file_path.get()}")
            yield from preamp1_netcdf.setup_file_writer(
                savedata,
                det_foldername["preamp1"],
                num_pulses,
                filename=filename,
                beamline_delimiter=netcdf_delimiter,
            )
        
            yield from preamp1_netcdf.set_capture("capturing")

        

    # """Print the scan parameters and the updated file name """
    # parm_list = [
    #     "samplename",
    #     "user_comments",
    #     "width",
    #     "x_center",
    #     "stepsize_x",
    #     "height",
    #     "y_center",
    #     "stepsize_y",
    #     "dwell",
    #     "inc_eng",
    #     "adjust_zp",
    #     "xrf_on",
    #     "preamp1_on",
    #     "preamp2_on",
    # ]
    # local_parms = locals()
    # parm_dict = {parm: local_parms[parm] for parm in parm_list}
    # logger.info(
    #     f"-------------------------------- File {savedata.next_file_name} "
    #     f"--------------------------------"
    # )
    # logger.info(f"Scan parameters: {parm_dict}")
    # logger.info(
    #     f"-------------------------------- File {savedata.next_file_name} --------------------------------"
    # )

    """Start executing scan"""
    # yield from bps.sleep(1)
    fname = savedata.next_file_name
    yield from execute_scan_2d(fscanh, fscan1, scan_name=fname, print_outter_msg=True)

    # """Enable the usercalc that used in scan record"""
    # yield from enable_usercalc()


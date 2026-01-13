"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    fly2d
""".split()

import logging

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import oregistry
from apsbits.utils.config_loaders import get_config

from mic_common.plans.generallized_scan_1d import generalized_scan_1d
from mic_common.utils.param_capture import capture_params
from mic_common.utils.scan_monitor import execute_scan_2d
from s2idd_uprobe.plans.before_after_fly import setup_flyscan_XRF_triggers, setup_flyscan_tmm_triggers
# from s2idd_uprobe.plans.helper_funcs import selected_dets
from s2idd_uprobe.plans.toggle_usercalc import disable_usercalc
from s2idd_uprobe.plans.toggle_usercalc import enable_usercalc
import numpy as np

logger = logging.getLogger(__name__)

det_foldername = {"xrf": "flyXRF", "preamp1": "tetramm", "preamp2": "tetramm2"}

fscan1 = oregistry["fscan1"]
fscanh = oregistry["fscanh"]
fscanh_dwell = oregistry["fscanh_dwell"]
fscanh_samx = oregistry["fscanh_samx"]
samx = oregistry["samx"]
samy = oregistry["samy"]
samz = oregistry["samz"]
savedata = oregistry["savedata"]
sis3820 = oregistry["sis3820"]
xrf = oregistry["xrf"]
xrf_netcdf = oregistry["xrf_netcdf"]
preamp1_hdf = oregistry["tmm1_hdf"]
preamp1 = oregistry["tmm1"]
iconfig = get_config()
scan_overhead = iconfig.get("SCAN_OVERHEAD")
netcdf_delimiter = iconfig.get("FILE_DELIMITER")
xmap_buffer = iconfig.get("XMAP")["BUFFER"]


def fly2d_scanrecord(
    samplename: str = "smp1",
    user_comments: str = "",
    width: float = 0,
    x_center: float = None,
    stepsize_x: float = 0,
    height: float = 0,
    y_center: float = None,
    stepsize_y: float = 0,
    dwell_ms: float = 0,
    sample_z: float = None,
    xrf_on: bool = True,
    preamp1_on: bool = False,
    preamp2_on: bool = False,
):
    """2D Bluesky plan that drives the x- and y- sample motors in fly mode using ScanRecord

    Parameters
    ----------
    samplename:
        The name of the sample for file naming. Default: "smp1". Type: str
    user_comments:
        User comments to be recorded with the scan data. Default is "". Type: str
    width:
        The total width of the scan area in microns. Default: 0. Type: float
    x_center:
        The center position of the scan in the x-direction in microns. If not provided, the current x-motor position will be used as the center. Default: None. Type: float
    stepsize_x:
        The step size (spatial resolution) in the x-direction in microns. Default: 0. Type: float
    height:
        The total height of the scan area in microns. Default: 0. Type: float
    y_center:
        The center position of the scan in the y-direction in microns. If not provided, the current y-motor position will be used as the center. Default: None. Type: float
    stepsize_y:
        The step size (spatial resolution) in the y-direction in microns. Default: 0. Type: float
    dwell_ms:
        The dwell time per step in milliseconds. Default: 0. Type: float
    sample_z:
        The sample z position in millimeters. If not provided, the current sample z position will be maintained. Default: None. Type: float
    xrf_on:
        Whether to enable the x-ray fluorescence detector. Default is True. Type: bool
    preamp1_on:
        Whether to enable preamp1. Preamp1 is used to record metadata. Default is True. Type: bool
    preamp2_on:
        Whether to enable preamp2. Default is False. Type: bool
    """

    """Capture the input plan parameters"""
    if x_center is None:
        x_center = samx.position
    if y_center is None:
        y_center = samy.position
    if sample_z is None:
        sample_z = samz.position

    plan_args = capture_params(fly2d_scanrecord, **locals())
    scan_id = None
    try:
        scan_id = savedata.next_scan_number.get()
    except Exception as e:
        logger.error(f"Error getting scan id: {e}")
        scan_id = None

    md = {"plan_args": plan_args, "scan_id": scan_id}

    @bpp.run_decorator(md=md)
    def _fly2d():
        yield from _fly2d_scanrecord(**plan_args)

    yield from _fly2d()


def _fly2d_scanrecord(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
    height=0,
    y_center=None,
    stepsize_y=0,
    dwell_ms=0,
    sample_z=None,
    xrf_on=True,
    preamp1_on=False,
    preamp2_on=False,
):
    """Disable the usercalc that used in scan record"""
    yield from disable_usercalc()

    """Move the sample to the requested z position"""
    if sample_z is not None:
        yield from bps.mv(samz, sample_z)
    if x_center is not None:
        yield from bps.mv(samx, x_center)
    if y_center is not None:
        yield from bps.mv(samy, y_center)

    """Set up inner scan record based on the scan types and parameters"""
    yield from generalized_scan_1d(
        scanrecord=fscanh,
        savedata=savedata,
        scan_overhead=scan_overhead,
        scanmode="FLY",
        x_center=samx.position,
        width=width,
        stepsize_x=stepsize_x,
        dwell=dwell_ms,
    )
    yield from fscanh.set_positioner_drive(f"{fscanh_samx.pvname}")

    """Set up the outter loop scan record"""
    yield from bps.mv(fscan1.positioners.p1.abs_rel, "relative".upper())
    yield from fscan1.set_positioner_drive(f"{samy.prefix}.VAL")
    yield from fscan1.set_positioner_readback(f"{samy.prefix}.RBV")

    """check if the scan movement is relative or absolute"""
    scan_movement = fscan1.scan_movement.enum_strs[fscan1.scan_movement.get()]
    if scan_movement == "RELATIVE":
        yield from fscan1.set_center_width_stepsize(0, height, stepsize_y)
    else:
        yield from fscan1.set_center_width_stepsize(y_center, height, stepsize_y)

    """Assign the per-pixel dwell time"""
    logger.info(f"Setting per-pixel dwell time ({fscanh_dwell.pvname}) to {dwell_ms} ms")
    yield from bps.mv(fscanh_dwell, dwell_ms)

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
            # num_capture = 0  # When it's zero, the num_capture won't be overwritten
            logger.info(f"xmap_buffer: {xmap_buffer}")
            logger.info(f"num_pulses: {num_pulses}")
            num_capture = int(np.ceil(num_pulses / xmap_buffer))
            yield from setup_flyscan_XRF_triggers(fscanh, xrf, xrf_netcdf, sis3820, num_pulses, 
                                                  motor_resolution=samx.resolution.get(), stepsize_x=stepsize_x,
                                                  update_prescale=True)
            yield from xrf.before_flyscan(num_pulses)
            yield from xrf_netcdf.setup_file_writer(
                savedata,
                det_foldername["xrf"],
                num_capture,
                filename=filename,
                beamline_delimiter=netcdf_delimiter,
            )
            fscan1.save_current_detTriggers()
            fscan1.clear_detTriggers()
            fscan1.save_bspv()
            fscan1.bspv.put('')
            yield from fscan1.set_detTriggers([fscanh.execute_scan.pvname,'','',''])
            # yield from xrf_netcdf.set_capture("capturing")

        if all([preamp1_on, preamp1_hdf.connected]):
            logger.info(f"Setting up file writer for preamp1, {preamp1_hdf.file_path.get()}")
            yield from preamp1.before_flyscan(num_pulses, dwell_ms, acquire_mode = "Multiple", 
                       dwell_fraction = 0.9)
            yield from setup_flyscan_tmm_triggers(fscan1, fscanh, preamp1, preamp1_hdf)

            yield from preamp1_hdf.setup_file_writer(
                savedata,
                det_foldername["preamp1"],
                num_pulses,
                filename=filename,
                beamline_delimiter=netcdf_delimiter,
            )
            # yield from preamp1_hdf.set_capture("capturing")

    """Start executing scan"""
    # yield from bps.sleep(1)
    fname = savedata.next_file_name
    yield from execute_scan_2d(fscanh, fscan1, scan_name=fname, print_outter_msg=True)

    """Enable the usercalc that used in scan record"""
    yield from enable_usercalc()
    yield from fscanh.restore_detTriggers()
    if preamp1_on:
        yield from fscan1.restore_detTriggers()
    fscan1.restore_bspv()
    

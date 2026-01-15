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

    """Set up inner / outer scan record based on the scan types and parameters"""
    inner_scanrecord_triggers = []
    outer_scanrecord_triggers = []
    if xrf_on and xrf.connected and xrf_netcdf.connected:
        try:
            inner_scanrecord_triggers.append(xrf_netcdf.capture.pvname.replace("_RBV", ""))
            inner_scanrecord_triggers.append(xrf.erase_start.pvname)
            inner_scanrecord_triggers.append(sis3820.erase_start.pvname)
        except Exception as e:
            logger.error(f"Error adding xrf_netcdf capture trigger to inner scanrecord: {e}")

    if preamp1_on and preamp1_hdf.connected:
        try:
            inner_scanrecord_triggers.append(preamp1_hdf.capture.pvname.replace("_RBV", ""))
            inner_scanrecord_triggers.append(preamp1.acquire.pvname)
            inner_scanrecord_triggers.append(fscanh.execute_scan.pvname)
        except Exception as e:
            logger.error(f"Error adding preamp1_hdf capture trigger to inner scanrecord: {e}")

    fscanh.config(
        positioner_setpoint=f"{fscanh_samx.pvname}",
        scanmode="FLY",
        center=samx.position,
        width=width,
        stepsize=stepsize_x,
        triggers=inner_scanrecord_triggers,
    )

    fscan1.config(
        positioner_setpoint=samy.user_setpoint.pvname,
        positioner_readback=samy.user_readback.pvname,
        rel_abs_motion="RELATIVE",
        center=0,
        width=height,
        stepsize=stepsize_y,
        triggers=outer_scanrecord_triggers,
    )

    fscanh.stage()
    fscan1.stage()

    """Assign the per-pixel dwell time"""
    logger.info(f"Setting per-pixel dwell time ({fscanh_dwell.pvname}) to {dwell_ms} ms")
    yield from bps.mv(fscanh_dwell, dwell_ms)

    """Update the next file name for the detector file plugin"""
    savedata.update_next_file_name()
    next_file_name = savedata.next_file_name

    # """Generate scan_master.h5 file"""

    """Initialize detectors with desired pts, exposure time and file writer """
    numpts_x = fscanh.number_points.value
    num_pulses = numpts_x - 2
    num_capture = int(np.ceil(num_pulses / xmap_buffer))
    filename = next_file_name.replace(".mda", "")
    dets = []

    if sis3820.connected:
        sis3820.config_before_flyscan(num_pulses, update_prescale=True, stepsize=stepsize_x, 
                                      motor_resolution=samx.resolution.get())
        dets.append(sis3820)
        
    if xrf_on and xrf.connected and xrf_netcdf.connected:
        xrf.config_before_flyscan(num_pulses)
        xrf_netcdf.config_file_writer(savedata, det_foldername["xrf"], num_capture, filename=filename, 
                                      beamline_delimiter=netcdf_delimiter)
        dets.append(xrf)
        dets.append(xrf_netcdf)

    if preamp1_on and preamp1.connected and preamp1_hdf.connected:
        preamp1.config_before_flyscan(num_pulses, dwell_ms)
        preamp1_hdf.config_file_writer(savedata, det_foldername["preamp1"], num_pulses, filename=filename, 
                                      beamline_delimiter=netcdf_delimiter)
        dets.append(preamp1)
        dets.append(preamp1_hdf)

    for det in dets:
        det.stage()

    """Start executing scan"""
    fname = savedata.next_file_name
    yield from execute_scan_2d(fscanh, fscan1, scan_name=fname, print_outter_msg=True)

    """Enable the usercalc that used in scan record"""
    yield from enable_usercalc()
    fscanh.unstage()
    fscan1.unstage()
    for det in dets:
        det.unstage()
    # yield from fscanh.restore_detTriggers()
    # if preamp1_on:
    #     yield from fscan1.restore_detTriggers()
    # fscan1.restore_bspv()
    

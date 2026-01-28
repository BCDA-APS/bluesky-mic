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
from mic_common.utils.scan_monitor import execute_scan_1d

# from s2idd_uprobe.plans.before_after_fly import setup_flyscan_XRF_triggers, setup_flyscan_tmm_triggers
# from s2idd_uprobe.plans.helper_funcs import selected_dets
from s2idd_uprobe.plans.toggle_usercalc import disable_usercalc
from s2idd_uprobe.plans.toggle_usercalc import enable_usercalc
from s2idd_uprobe.plans.stepscan_core import _common_stepscan_setup
from s2idd_uprobe.utils.fly import get_next_file_name

logger = logging.getLogger(__name__)

det_foldername = {"xrf": "flyXRF", "preamp1": "tetramm", "preamp2": "tetramm2"}


scan1 = oregistry["scan1"]
samx = oregistry["samx"]
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
xmap_buffer = iconfig.get("XMAP", "BUFFER")


def step1d_scanrecord(
    samplename: str = "smp1",
    user_comments: str = "",
    width: float = 0,
    x_center: float = None,
    stepsize_x: float = 0,
    dwell_ms: float = 0,
    sample_z: float = None,
    xrf_on: bool = True,
    preamp1_on: bool = False,
):
    """1D Bluesky plan that drives the x- sample motors in step mode using ScanRecord

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
    if sample_z is None:
        sample_z = samz.position

    plan_args = capture_params(step1d_scanrecord, **locals())
    scan_id = None
    try:
        scan_id = savedata.next_scan_number.get()
    except Exception as e:
        logger.error(f"Error getting scan id: {e}")
        scan_id = None

    md = {"plan_args": plan_args, "scan_id": scan_id}

    @bpp.run_decorator(md=md)
    def _step1d():
        yield from _step1d_scanrecord(**plan_args)

    yield from _step1d()


def _step1d_scanrecord(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
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

    """Set up inner scan record based on the scan types and parameters"""
    yield from bps.mv(scan1.positioners.p1.abs_rel, "relative".upper())
    yield from generalized_scan_1d(
        scanrecord=scan1,
        savedata=savedata,
        scan_overhead=scan_overhead,
        scanmode="LINEAR",
        x_center=0,
        width=width,
        stepsize_x=stepsize_x,
        dwell=dwell_ms,
        positioner=samx,
    )

    """Setup the detectors and file I/O"""
    total_pts = scan1.number_points.get()
    filename = get_next_file_name(savedata)
    preamp2_on = False
    devices_dict, fileplugins_dict = yield from _common_stepscan_setup(
        xrf_on, preamp1_on, preamp2_on, total_pts, dwell_ms, filename
    )

    if preamp1.connected and preamp1_on == False:
        yield from preamp1.set_single_acquire()

    """Start executing scan"""
    fname = savedata.next_file_name
    yield from execute_scan_1d(scan1, scan_name=fname)

    """Enable the usercalc that used in scan record"""
    yield from enable_usercalc()

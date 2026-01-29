"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    step1d_scanrecord
""".split()

# import logging

# import bluesky.plan_stubs as bps
# import bluesky.preprocessors as bpp
# from apsbits.core.instrument_init import oregistry
# from apsbits.utils.config_loaders import get_config

# from mic_common.plans.generallized_scan_1d import generalized_scan_1d
# from mic_common.utils.param_capture import capture_params
# from mic_common.utils.scan_monitor import execute_scan_1d

# # from s2idd_uprobe.plans.before_after_fly import setup_flyscan_XRF_triggers, setup_flyscan_tmm_triggers
# # from s2idd_uprobe.plans.helper_funcs import selected_dets
# from s2idd_uprobe.plans.toggle_usercalc import disable_usercalc
# from s2idd_uprobe.plans.toggle_usercalc import enable_usercalc
# from s2idd_uprobe.plans.stepscan_core import _common_stepscan_setup
# from s2idd_uprobe.utils.fly import get_next_file_name

# logger = logging.getLogger(__name__)

# # det_foldername = {"xrf": "flyXRF", "preamp1": "tetramm", "preamp2": "tetramm2"}


# # scan1 = oregistry["scan1"]
# # samx = oregistry["samx"]
# # samz = oregistry["samz"]
# # savedata = oregistry["savedata"]
# # sis3820 = oregistry["sis3820"]
# # xrf = oregistry["xrf"]
# # xrf_netcdf = oregistry["xrf_netcdf"]
# # preamp1_hdf = oregistry["tmm1_hdf"]
# # preamp1 = oregistry["tmm1"]
# # iconfig = get_config()
# # scan_overhead = iconfig.get("SCAN_OVERHEAD")
# # netcdf_delimiter = iconfig.get("FILE_DELIMITER")
# # xmap_buffer = iconfig.get("XMAP", "BUFFER")




import logging
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import oregistry
from mic_common.utils.validation import validate_scan_parameters, validate_device_connections
from s2idd_uprobe.utils.step import setup_detectors_and_fileio
from s2idd_uprobe.plans.toggle_usercalc import enable_usercalc, disable_usercalc
from mic_common.utils.param_capture import capture_params

logger = logging.getLogger(__name__)

sample = oregistry["sample"]
scanrecord = oregistry["scanrecord"]
scaler_count = oregistry["scaler_count"]
savedata = oregistry["savedata"]

def _step1d_scanrecord(
    width=0,
    x_center=None,
    stepsize_x=0,
    dwell_ms=0,
    sample_z=None,
    xrf_on=True,
    preamp1_on=False,
    **kwargs,
):
    """Check input parameters and detector status"""
    logger.info("Validating scan parameters and detector status")
    validate_scan_parameters(stepsize_x=stepsize_x, width=width, dwell_ms=dwell_ms)
    x_center = x_center if x_center is not None else (round(sample.x.position - width / 2, 2))
    sample_z = sample_z if sample_z is not None else (round(sample.z.position, 2))
    yield from bps.mv(sample.x, x_center)
    yield from bps.mv(sample.z, sample_z)

    det_bools = [xrf_on, preamp1_on]
    det_names = ["xrf", "tmm1"]
    devices = validate_device_connections(det_bools, det_names, return_devices=True)
    
    """Disable the usercalc that used in scan record"""
    # yield from disable_usercalc()

    """Set up scan record"""
    yield from scanrecord.step.stage1Dstep(
        devices, scaler_count, sample.x, width, stepsize_x
    )

    """Setup the detectors and file I/O"""
    setup_detectors_and_fileio(devices, dwell_time=dwell_ms)
    yield from bps.checkpoint()

    """Start executing scan"""
    fname = savedata.next_file_name
    yield from scanrecord.step.execute1Dstep(scan_name=fname)
    yield from bps.checkpoint()

    """Scan cleanup"""
    # yield from enable_usercalc()
    yield from bps.sleep(0.5)
    yield from scanrecord.step.unstage1Dstep()
    for d in devices:
        d.unstage()


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
    """

    """Capture the input plan parameters"""
    x_center = round(sample.x.position, 2) if x_center is None else x_center
    sample_z = round(sample.z.position, 2) if sample_z is not None else sample_z

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

"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    step1d_scanrecord
""".split()



import logging
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import oregistry
from mic_common.utils.validation import validate_scan_parameters, validate_device_connections
from s2idd_uprobe.utils.step import setup_detectors_and_fileio
from s2idd_uprobe.plans.toggle_usercalc import enable_usercalc, disable_usercalc
from mic_common.utils.param_capture import capture_params

logger = logging.getLogger(__name__)

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
    
    """Load ophyd objects"""
    sample = oregistry["sample"]
    scanrecord = oregistry["scanrecord"]
    scaler_count = oregistry["scaler_count"]
    savedata = oregistry["savedata"]

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

    sample = oregistry['sample']
    savedata = oregistry['savedata']


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

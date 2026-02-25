"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    step1d_scanrecord
    xanes_1d
""".split()



import logging
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import oregistry
from mic_common.utils.validation import validate_device_connections
from s2idd_uprobe.utils.step import setup_detectors_and_fileio
from s2idd_uprobe.plans.toggle_usercalc import enable_usercalc, disable_usercalc
from mic_common.utils.param_capture import capture_params
from s2idd_uprobe.utils.step import setup_detectors_and_fileio

logger = logging.getLogger(__name__)

"""Load ophyd objects"""
scanrecord = oregistry["scanrecord"]
savedata = oregistry["savedata"]
flycalc = oregistry['fly_calc10']
sample = oregistry['sample']
mono = oregistry['kohzu_mono']
scaler_count = oregistry['scaler_count']


def _step1d_scanrecord(
    positioner_name: str = "x", # available: "x", "y", "z", "energy"
    width: float = 0,
    center: float = 0,
    stepsize_x: float = 0,
    dwell_ms: float = 0,
    sample_x: float = None,
    sample_y: float = None,
    sample_z: float = None,
    energy: float = None,
    xrf_on: bool = True,
    preamp1_on: bool = False,
    **kwargs,
):

    """Look for positioner"""
    if positioner_name == "x":
        positioner = sample.x
    elif positioner_name == "y":
        positioner = sample.y
    elif positioner_name == "z":
        positioner = sample.z
    elif positioner_name == "energy":
        positioner = mono
    else:
        raise ValueError(f"Invalid positioner name: {positioner_name}")    

    """Move to desired positions"""
    yield from bps.mv(sample.x, sample_x)
    yield from bps.mv(sample.y, sample_y)
    yield from bps.mv(sample.z, sample_z)
    yield from bps.mv(mono, energy)

    """Validate / select detectors and stage scan record"""
    det_bools = [xrf_on, preamp1_on]
    det_names = ["xrf", "tmm1"]
    devices = validate_device_connections(det_bools, det_names, return_devices=True)
    yield from scanrecord.step.stage1Dstep(devices, scaler_count, positioner, width, center, stepsize_x)

    """Setup the detectors and file I/O"""
    setup_detectors_and_fileio(devices, dwell_time=dwell_ms)
    yield from bps.checkpoint()

    """Disable the usercalc that used in scan record"""
    # yield from disable_usercalc()
    if flycalc.value == 0:
        yield from bps.mv(flycalc, 1)

    """Start executing scan"""
    fname = savedata.next_file_name
    yield from scanrecord.step.execute1Dstep(scan_name=fname)
    yield from bps.checkpoint()

    """Scan cleanup"""
    yield from enable_usercalc()
    yield from bps.sleep(1)
    yield from scanrecord.step.unstage1Dstep()
    for d in devices:
        d.unstage()
    yield from bps.mv(flycalc, 0)


def step1d_scanrecord(
    samplename: str = "smp1",
    user_comments: str = "",
    positioner_name: str = "x", 
    width: float = 0,
    center: float = 0,
    stepsize_x: float = 0,
    dwell_ms: float = 0,
    sample_x: float = None,
    sample_y: float = None,
    sample_z: float = None,
    energy: float = None,
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
    positioner_name:
        The name of the positioner to be scanned. Default: "x". Other options: "y", "z", "energy"
    width:
        The total width of the positioner scan range. Default: 0. Type: float
    center:
        The center position of the positioner scan range. Default: 0. Type: float
    stepsize_x:
        The step size (spatial resolution) in the x-direction in microns. Default: 0. Type: float
    dwell_ms:
        The dwell time per step in milliseconds. Default: 0. Type: float
    sample_x:
        The sample x position in millimeters. If not provided, the current sample x position will be maintained. Default: None. Type: float
    sample_y:
        The sample y position in millimeters. If not provided, the current sample y position will be maintained. Default: None. Type: float
    sample_z:
        The sample z position in millimeters. If not provided, the current sample z position will be maintained. Default: None. Type: float
    energy:
        The energy in keV. If not provided, the current energy will be maintained. Default: None. Type: float
    xrf_on:
        Whether to enable the x-ray fluorescence detector. Default is True. Type: bool
    preamp1_on:
        Whether to enable preamp1. Preamp1 is used to record metadata. Default is True. Type: bool
    """

    """Capture the input plan parameters"""
    sample_x = round(sample.x.position, 2) if sample_x is None else sample_x
    sample_y = round(sample.y.position, 2) if sample_y is None else sample_y
    sample_z = round(sample.z.position, 2) if sample_z is None else sample_z
    energy = round(mono.user_readback.get(), 4) if energy is None else energy

    plan_args = capture_params(step1d_scanrecord, **locals())
    scan_id = savedata.next_scan_number.get()

    print(f"scan_id: {scan_id}")
    md = {"plan_args": plan_args, "scan_id": scan_id}

    @bpp.run_decorator(md=md)
    def _step1d():
        yield from _step1d_scanrecord(**plan_args)

    yield from _step1d()


def xanes_1d(
    samplename: str = "smp1",
    user_comments: str = "",
    width_keV: float = 0,
    center_keV: float = 0,
    stepsize_keV: float = 0,
    dwell_ms: float = 0,
    sample_x: float = None,
    sample_y: float = None,
    sample_z: float = None,
    energy: float = None,
    xrf_on: bool = True,
    preamp1_on: bool = False,
):

    """1D Bluesky plan that drives the energy in step mode using ScanRecord
    
    Parameters
    ----------
    samplename: str
        The name of the sample for file naming. Default: "smp1". Type: str
    user_comments: str
        User comments to be recorded with the scan data. Default is "". Type: str
    width_keV: float
        The total width of the energy scan range in keV. Default: 0. Type: float
    center_keV: float
        The center position of the energy scan range in keV. Default: 0. Type: float
    stepsize_keV: float
        The step size (energy resolution) in the x-direction in keV. Default: 0. Type: float
    dwell_ms: float
        The dwell time per step in milliseconds. Default: 0. Type: float
    sample_x: float
        The sample x position in millimeters. If not provided, the current sample x position will be maintained. Default: None. Type: float
    sample_y: float
        The sample y position in millimeters. If not provided, the current sample y position will be maintained. Default: None. Type: float
    sample_z: float
        The sample z position in millimeters. If not provided, the current sample z position will be maintained. Default: None. Type: float
    energy: float
        The energy in keV. If not provided, the current energy will be maintained. Default: None. Type: float
    xrf_on: bool
        Whether to enable the x-ray fluorescence detector. Default is True. Type: bool
    preamp1_on: bool
        Whether to enable preamp1. Preamp1 is used to record metadata. Default is True. Type: bool
    """
    positioner_name = "energy"
    width = width_keV
    center = center_keV
    stepsize_x = stepsize_keV

    yield from step1d_scanrecord(
        samplename=samplename,
        user_comments=user_comments,
        positioner_name=positioner_name,
        width=width,
        center=center,
        stepsize_x=stepsize_x,
        dwell_ms=dwell_ms,
        sample_x=sample_x,
        sample_y=sample_y,
        sample_z=sample_z,
        energy=energy,
        xrf_on=xrf_on,
        preamp1_on=preamp1_on,
    )

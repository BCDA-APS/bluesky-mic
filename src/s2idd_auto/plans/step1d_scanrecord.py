"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    step1d_scanrecord
    xanes_1d
""".split()



import logging
from decimal import Decimal
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


def build_energy_setpoints_eV(energy_list_eV: list[float], stepsize_list_eV: list[float]) -> list[float]:
    """Expand energy breakpoints into explicit setpoints.

    Convention:
    - `energy_list_eV` contains ordered breakpoint energies.
    - `stepsize_list_eV[i]` is used for the segment from `energy_list_eV[i]` to
      `energy_list_eV[i+1]`.
    - The final endpoint is included once.

    `stepsize_list_eV` may be the same length as `energy_list_eV`; in that case
    the last step size is ignored.
    """
    if len(energy_list_eV) < 2:
        raise ValueError("energy_list_eV must contain at least two energies.")

    if len(stepsize_list_eV) not in (len(energy_list_eV) - 1, len(energy_list_eV)):
        raise ValueError(
            "stepsize_list_eV must have length len(energy_list_eV)-1 "
            "or len(energy_list_eV)."
        )

    energies = [Decimal(str(v)) for v in energy_list_eV]
    steps = [Decimal(str(v)) for v in stepsize_list_eV[: len(energy_list_eV) - 1]]
    print(f"energies: {energies}")
    print(f"steps: {steps}")

    setpoints: list[Decimal] = [energies[0]]
    for i, step in enumerate(steps):
        start = energies[i]
        stop = energies[i + 1]
        if step <= 0:
            raise ValueError(f"Step size must be > 0 for segment {i}.")
        if stop <= start:
            raise ValueError("energy_list_eV must be strictly increasing.")

        current = start
        while current + step < stop:
            current += step
            setpoints.append(current)

        if setpoints[-1] != stop:
            setpoints.append(stop)

    return [float(v) for v in setpoints]


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
    setpoint_list: list[float] = None,
    table_mode: bool = False,
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
    if not table_mode:
        yield from scanrecord.step.stage1Dstep(devices, 
                                           scaler_count,
                                           positioner, width, 
                                           center, stepsize_x)
    else:
        yield from scanrecord.step.stage1Dstep_TabelMode(devices, 
                                           scaler_count,
                                           positioner, setpoint_list)

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

    """Set the x motor speed back to default, patch fix during Mariana's beamtime 2026c1"""
    yield from bps.mv(sample.x.velocity, sample.x.max_velocity.get())


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
    setpoint_list: list[float] = None,
    table_mode: bool = False,
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
    setpoint_list:
        List of energy breakpoints in eV. Default: None. Type: list[float]
    table_mode:
        Whether to use table mode. Default: False. Type: bool
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



def xanes_1d_nonlinear_step(
    samplename: str = "smp1",
    user_comments: str = "",
    energy_list_eV: list = [],
    stepsize_list_eV: list = [],
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
    energy_list_eV: list
        The energy list in eV. Default: []
    stepsize_list_eV: list
        The step size list in eV. Default: []
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
    energy_list_eV = build_energy_setpoints_eV(energy_list_eV, stepsize_list_eV)
    energy_list = [e/1000 for e in energy_list_eV]
    table_mode = True   

    yield from step1d_scanrecord(
        samplename=samplename,
        user_comments=user_comments,
        positioner_name=positioner_name,
        dwell_ms=dwell_ms,
        sample_x=sample_x,
        sample_y=sample_y,
        sample_z=sample_z,
        energy=energy,
        xrf_on=xrf_on,
        preamp1_on=preamp1_on,
        setpoint_list=energy_list,
        table_mode=table_mode,
    )



def xanes_1d_linear(
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

    yield from bps.sleep(40)
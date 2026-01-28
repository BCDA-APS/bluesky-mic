"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    step2d_scanrecord
    step1d_focusing_x
    step1d_focusing_y
""".split()

import logging
import inspect
from apsbits.utils.controls_setup import oregistry
from mic_common.utils.scan_monitor import execute_scan_2d, execute_scan_1d
from mic_common.plans.generallized_scan_1d import generalized_scan_1d
from bluesky import plan_stubs as bps
from apsbits.utils.config_loaders import get_config
from s2ide_uprobe.utils.usercalc_lib import hydra_config, sis3820_config, xrf_config
from s2ide_uprobe.plans.toggle_usercalc import enable_usercalc, disable_usercalc
from ophyd.status import Status
from apstools.plans import run_blocking_function
# from s2ide_uprobe.plans.before_after_fly import setup_flyscan_ptycho_triggers, setup_flyscan_XRF_triggers
from apsbits.utils.config_loaders import get_config
from mic_common.utils.param_capture import capture_params
import bluesky.preprocessors as bpp

logger = logging.getLogger(__name__)
logger.info(__file__)

scan1 = oregistry["scan1"]
scan2 = oregistry["scan2"]
samx = oregistry["samx"]
samy = oregistry["samy"]
zp_z = oregistry["zp_z"]
samtheta = oregistry["samtheta"]
savedata = oregistry["savedata"]
xrf = oregistry["xrf"]


iconfig = get_config()
scan_overhead = iconfig.get("SCAN_OVERHEAD")
xmap_buffer = iconfig.get("XMAP", "BUFFER")
netcdf_delimiter = iconfig.get("FILE_DELIMITER")
det_foldername = {"xrf": "flyXRF", "preamp1": "tetramm", "preamp2": "tetramm2", "ptycho": "ptycho"}


def step2d_scanrecord(
    samplename="smp1",
    user_comments="",
    width_mm=0,
    x_center_mm=None,
    stepsize_x_mm=0,
    height_mm=0,
    y_center_mm=None,
    stepsize_y_mm=0,
    dwell_ms=0,
    smp_theta=None,
):
    """2D Bluesky plan that drives the x- and y- sample motors in stepping mode using
    ScanRecord

    The plan will drive samx and samy to the requested x_center and y_center,
    and then perform a relative scan in the x and y directions.

    Parameters
    ----------
    samplename:
        Str: The name of the sample
    user_comments:
        Str: The user comments for the scan
    width_mm:
        Float: The width of the scan in unit of mm
    x_center_mm:
        Float: The center of the scan in the x direction. Default is None which uses the current position of samx
    stepsize_x_mm:
        Float: The step size in the x direction in unit of mm
    height_mm:
        Float: The height of the scan in unit of mm
    y_center_mm:
        Float: The center of the scan in the y direction. Default is None which uses the current position of samy
    stepsize_y_mm:
        Float: The step size in the y direction in unit of mm
    dwell_ms:
        Float: The dwell time in the scan in unit of ms
    smp_theta:
        Float: The theta of the sample
    """

    """Capture the input plan parameters"""
    plan_args = capture_params(step2d_scanrecord, **locals())
    md = {"plan_args": plan_args}

    @bpp.run_decorator(md=md)
    def _step2d():
        yield from _step2d_scanrecord(**plan_args)

    yield from _step2d()


def step1d_focusing_x(
    samplename: str = "smp1",
    user_comments: str = "",
    width_mm: float = 0,
    x_center_mm: float = None,
    stepsize_x_mm: float = 0,
    samz_mm: float = None,
    dwell_ms: float = 0,
    zp_z_mm: float = None,
):
    """Step 1D focusing plan that drives the samx motor. 
       If zp_z_mm is not provided, the plan will use the current 
       position of zp_z"""

    if x_center_mm is None:
        x_center_mm = samx.position
    if samz_mm is None:
        samz_mm = samz.position
    if zp_z_mm is None:
        zp_z_mm = zp_z.position

    plan_args = capture_params(step1d_focusing_x, **locals())
    md = {"plan_args": plan_args}
    plan_args["exec_plan"] = True

    if xrf.connected:
        yield from xrf.stepscan_before()
        yield from xrf.set_real_time(dwell_ms / 1e3)

    @bpp.run_decorator(md=md)
    def _step1d():
        args = {samplename: samplename, 
                user_comments: user_comments, 
                width_mm: width_mm, 
                center_mm: x_center_mm, 
                stepsize_mm: stepsize_x_mm, 
                samz_mm: samz_mm, 
                zp_z_mm: zp_z_mm, 
                dwell_ms: dwell_ms,
                positioner: 'x'}
        yield from _step1d_scanrecord(**args)

    yield from _step1d()


def step1d_focusing_y(
    samplename: str = "smp1",
    user_comments: str = "",
    height_mm: float = 0,
    y_center_mm: float = None,
    stepsize_y_mm: float = 0,
    samz_mm: float = None,
    dwell_ms: float = 0,
    zp_z_mm: float = None,
):
    """Step 1D focusing plan that drives the samy motor. 
       If zp_z_mm is not provided, the plan will use the current 
       position of zp_z"""

    if y_center_mm is None:
        y_center_mm = samy.position
    if samz_mm is None:
        samz_mm = samz.position
    if zp_z_mm is None:
        zp_z_mm = zp_z.position

    plan_args = capture_params(step1d_focusing_y, **locals())
    md = {"plan_args": plan_args}
    plan_args["exec_plan"] = True

    if xrf.connected:
        yield from xrf.stepscan_before()
        yield from xrf.set_real_time(dwell_ms / 1e3)

    @bpp.run_decorator(md=md)
    def _step1d():
        args = {samplename: samplename, 
                user_comments: user_comments, 
                width_mm: height_mm, 
                center_mm: y_center_mm, 
                stepsize_mm: stepsize_y_mm, 
                samz_mm: samz_mm, 
                zp_z_mm: zp_z_mm, 
                dwell_ms: dwell_ms,
                positioner: 'y'}
        yield from _step1d_scanrecord(**args)

    yield from _step1d()


def _step1d_scanrecord(
    samplename="smp1",
    user_comments="",
    width_mm=0,
    center_mm=None,
    stepsize_mm=0,
    samz_mm=None,
    zp_z_mm=None,
    dwell_ms=0,
    exec_plan=False,
    positioner: str = 'x',
):
    """1D Bluesky plan that drives the samx motor in stepping mode using ScanRecord"""

    """Before scan start, handle things were done using usercalc"""


    """Validate the input parameters"""
    if center_mm is None:
        raise ValueError("Center position cannot be None, please check the input parameters")
    if stepsize_mm == 0:
        raise ValueError("Step size cannot be 0, please check the input parameters")
    if dwell_ms == 0:
        raise ValueError("Dwell time cannot be 0, please check the input parameters")

    """Move to the requested z-position"""
    if samz_mm is not None:
        yield from bps.mv(samz, samz_mm)
    if zp_z_mm is not None:
        yield from bps.mv(zp_z, zp_z_mm)
    
    """Set up scan record based on the scan types and parameters"""
    yield from generalized_scan_1d(
        scanrecord=scan1,
        scanmode="LINEAR",
        x_center=center_mm,
        width=width_mm,
        stepsize_x=stepsize_mm,
        dwell=dwell_ms,
        savedata=savedata,
    )

    if positioner == 'x':
        yield from scan1.set_positioner_drive(f"{samx.prefix}.VAL")
    elif positioner == 'y':
        yield from scan1.set_positioner_drive(f"{samy.prefix}.VAL")
    else:
        raise ValueError(f"Invalid positioner: {positioner}")

    yield from scan1.set_positioner_readback("")
    yield from scan1.set_rel_abs_motion("ABSOLUTE")
    
    """Start executing scan"""
    if exec_plan:

        """Disable the usercalc that used in scan record"""
        yield from disable_usercalc()
        savedata.update_next_file_name()
        yield from execute_scan_1d(scan1, scan_name=savedata.next_file_name)
        yield from bps.sleep(1)

        """Enable the usercalc that used in scan record"""
        yield from enable_usercalc()


def _step2d_scanrecord(
    samplename="smp1",
    user_comments="",
    width_mm=0,
    x_center_mm=None,
    stepsize_x_mm=0,
    height_mm=0,
    y_center_mm=None,
    stepsize_y_mm=0,
    dwell_ms=0,
    smp_theta=None,
):

    ##TODO Close shutter while setting up scan parameters

    """Disable the usercalc that used in scan record"""
    yield from disable_usercalc()

    """Move sample theta to the requested angle"""
    if smp_theta is not None:
        yield from bps.mv(samtheta, smp_theta)
        yield from bps.sleep(1)
        logger.info(f"Moved sample theta to {smp_theta} degrees")

    """Move to the requested x- and y- positions"""
    if x_center_mm is not None:
        yield from bps.mv(samx, x_center_mm)
    else:
        x_center_mm = samx.position

    if y_center_mm is not None:
        yield from bps.mv(samy, y_center_mm)
    else:
        y_center_mm = samy.position

    """Validate the input parameters"""
    if stepsize_x_mm == 0:
        raise ValueError("Step size cannot be 0, please check the input parameters")
    if stepsize_y_mm == 0:
        raise ValueError("Step size cannot be 0, please check the input parameters")
    if dwell_ms == 0:
        raise ValueError("Dwell time cannot be 0, please check the input parameters")

    """Set up inner scan record"""
    yield from _step1d_scanrecord(
        samplename=samplename,
        user_comments=user_comments,
        width_mm=width_mm,
        x_center_mm=x_center_mm,
        stepsize_x_mm=stepsize_x_mm,
        dwell_ms=dwell_ms,
    )

    """Set up the outter loop scan record"""
    yield from scan2.set_scan_mode("linear")
    yield from scan2.set_positioner_drive(f"{samy.prefix}.VAL")
    yield from bps.sleep(0.2)
    yield from scan2.set_positioner_readback(f"{samy.prefix}.RBV")
    yield from scan2.set_rel_abs_motion("RELATIVE")
    yield from scan2.set_center_width_stepsize(0, height_mm, stepsize_y_mm)

    """Configure the XRF detector"""
    if xrf.connected:
        yield from xrf.stepscan_before()
        yield from xrf.set_real_time(dwell_ms / 1e3)

    """Update the next file name for the detector file plugin"""
    savedata.update_next_file_name()
    next_file_name = savedata.next_file_name
    filename = next_file_name.replace(".mda", "_XMAP")

    """Start executing scan"""
    yield from execute_scan_2d(scan1, scan2, scan_name=savedata.next_file_name, print_outter_msg=True)

    """Enable the usercalc that used in scan record"""
    yield from enable_usercalc()

import logging

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import oregistry
from apsbits.utils.config_loaders import get_config
from mic_common.utils.param_capture import capture_params

logger = logging.getLogger(__name__)

fscan_inner = oregistry["fscan_inner"]
fscan_outer = oregistry["fscan_outer"]
sample = oregistry["sample"]
savedata = oregistry["savedata"]
xrf = oregistry["xrf"]
xrf_netcdf = oregistry["xrf_netcdf"]
sis3820 = oregistry["sis3820"]
SM_PS_busy = oregistry["SM_PS_busy"]

def fly2d_scanrecord(
    sample_name: str = "sample",
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
    ptycho_on: bool = False,
    ptycho_exp_factor: float = 1,
):
    """2D Bluesky plan that drives the x- and y- sample motors in fly mode using ScanRecord

    Parameters
    ----------
    sample_name:
        The name of the sample for file naming. Default: "sample". Type: str
    user_comments:
        The user comments for the scan. Default: "". Type: str
    width:
        The width of the scan in unit of mm. Default: 0. Type: float
    x_center:
        The center of the scan in the x direction. Default is None which uses the current position of samx. Type: float
    stepsize_x:
        The step size in the x direction in unit of mm. Default: 0. Type: float
    height:
        The height of the scan in unit of mm. Default: 0. Type: float
    y_center:
        The center of the scan in the y direction. Default is None which uses the current position of samy. Type: float
    stepsize_y:
        The step size in the y direction in unit of mm. Default: 0. Type: float
    dwell_ms:
        The dwell time in the scan in unit of ms. Default: 0. Type: float
    sample_z:
        The z position of the sample. Default is None which uses the current position of samz. Type: float
    xrf_on:
        Whether to collect XRF data. Default: True. Type: bool
    ptycho_on:
        Whether to collect Ptycho data. Default: False. Type: bool
    ptycho_exp_factor:
        The exposure factor for the Ptycho detector. Default: 1. Type: float
    """

    """Capture the input plan parameters"""
    if x_center is None:
        x_center = sample.x.user_readback.get()
    if y_center is None:
        y_center = sample.y.user_readback.get()
    if sample_z is None:
        sample_z = sample.z.user_readback.get()

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
    sample_name: str = "sample",
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
    ptycho_on: bool = False,
    ptycho_exp_factor: float = 1,
):

    """Move the sample to the requested z position"""
    if sample_z is not None:
        yield from bps.mv(sample.z.user_setpoint, sample_z)
    if x_center is not None:
        yield from bps.mv(sample.x.user_setpoint, x_center)
    if y_center is not None:
        yield from bps.mv(sample.y.user_setpoint, y_center)

    """Set up inner / outer scan record based on the scan types and parameters"""
    inner_scanrecord_triggers = []
    outer_scanrecord_triggers = []
    if not sis3820.connected or not SM_PS_busy.connected:
        raise ValueError("SIS3820 and SM_PS_busy must be connected to use this plan")
    inner_scanrecord_triggers=[SM_PS_busy.pvname, '', '', sis3820.erase_start.pvname]

    if xrf_on and (not xrf.connected or not xrf_netcdf.connected or not fscan_inner.connected):
        raise ValueError("XRF and XRF_NETCDF must be connected to use this plan")
    outer_scanrecord_triggers=[xrf_netcdf.capture.pvname.replace("_RBV", ""), 
                               xrf.erase_start.pvname, 
                               '',
                               fscan_inner.execute_scan.pvname]

    fscan_inner.config(
        positioner_setpoint=sample.x.user_setpoint.pvname,
        positioner_readback=sample.x.user_readback.pvname,
        scanmode="FLY",
        rel_abs_motion="ABSOLUTE",
        center=x_center,
        width=width,
        stepsize=stepsize_x,
        trigger_pvs=inner_scanrecord_triggers,
    )

    fscan_outer.config(
        positioner_setpoint=sample.y.user_setpoint.pvname,
        positioner_readback=sample.y.user_readback.pvname,
        scanmode="LINEAR",
        rel_abs_motion="ABSOLUTE",
        center=y_center,
        width=height,
        stepsize=stepsize_y,
        trigger_pvs=outer_scanrecord_triggers,
    )

    fscan_inner.stage()
    fscan_outer.stage()


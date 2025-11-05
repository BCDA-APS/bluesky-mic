from apsbits.utils.config_loaders import get_config
from apsbits.core.instrument_init import oregistry
from isn.utils.param_capture import capture_params
import bluesky.preprocessors as bpp
from bluesky import plan_stubs as bps
from isn.plans.flyscan import flyscan

import logging
logger = logging.getLogger(__name__)
logger.info(__file__)

sample = oregistry["sample"]
me7 = oregistry["me7"]
ptycho = oregistry["ptycho"]

XSP3_MAX_PTS = 12000

def fly2d(
    samplename: str = "smp1",
    x_center: float = None,
    y_center: float = None,
    width: float = 0,
    height: float = 0,
    stepsize_x: float = 0,
    stepsize_y: float = 0,
    dwell_ms: float = 0,
    num_interferometer_per_pixel: int = 5,
    det_dead_ms: float = 20,
    sample_z: float = None,
    xrf_on: bool = True,
    ptycho_on: bool = False,
):

    """
    2D Bluesky plan that drives the x- and y- sample motors in flying mode
    The plan will drive samx and samy to the requested x_center and y_center, 
    and then perform a relative scan in the x and y directions.

    Parameters
    ----------
    samplename: 
        Str: The name of the sample
    x_center:
        Float: The center of the scan in the x direction. Default is None which uses the current position of samx
    y_center:
        Float: The center of the scan in the y direction. Default is None which uses the current position of samy
    width:
        Float: The width of the scan in um
    height:
        Float: The height of the scan in um
    stepsize_x:
        Float: The step size in the x direction in um
    stepsize_y:
        Float: The step size in the y direction in um
    dwell_ms:
        Float: The dwell time in the scan in ms
    det_dead_ms:
        Float: The detector dead time in the scan in ms
    sample_z:
        Float: The z position of the sample
    xrf_on:
        Bool: Whether to collect XRF data
    ptycho_on:
        Bool: Whether to collect Ptycho data
    """


    """Move to the requested x- and y- centers"""
    if x_center is not None:
        yield from bps.mv(sample.x, x_center)
    if y_center is not None:
        if not sample.y.enabled:
            sample.y.enable()
        yield from bps.mv(sample.y, y_center)

    """Capture the input plan parameters"""
    x_center = sample.x.user_readback.get()
    y_center = sample.y.user_readback.get()
    initial_args = capture_params(fly2d, **locals())

    y_piezo_center = 45
    x_min = -width/2
    x_max = width/2
    y_min = -height/2 + y_piezo_center
    y_max = height/2 + y_piezo_center
    x_npts = int(width/stepsize_x)
    y_npts = int(height/stepsize_y)
    acquire_time = dwell_ms
    det_dead = 20
    F = 0.9
    interferometer_frequency = 1000 * num_interferometer_per_pixel / (dwell_ms + det_dead_ms)

    total_pts = x_npts * (y_npts / F)
    if total_pts >= XSP3_MAX_PTS:
        raise ValueError(f"Total points {total_pts} is greater than the maximum allowed {XSP3_MAX_PTS}")
    
    """Define the detectors"""
    det = []
    if xrf_on:
        det.append(me7)
    if ptycho_on:
        det.append(ptycho)

    """Perform the scan"""
    plan_args = {
        "x_min": x_min,
        "x_max": x_max,
        "x_npts": x_npts,
        "y_min": y_min,
        "y_max": y_max,
        "y_npts": y_npts,
        "acquire_time": acquire_time,
        "det_dead": det_dead,
        "F": F,
        "interferometer_frequency": interferometer_frequency
    }

    md = {"plan_args": plan_args, "initial_args": initial_args}
    @bpp.run_decorator(md=md)
    def _fly2d():
        yield from flyscan(det, **plan_args)
    yield from _fly2d()

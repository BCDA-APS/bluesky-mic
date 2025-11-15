from apsbits.utils.config_loaders import get_config
from apsbits.core.instrument_init import oregistry
from isn.utils.param_capture import capture_params
from isn.plans.utils.scan_master_gen import generate_scan_master_h5
import bluesky.preprocessors as bpp
from bluesky import plan_stubs as bps
from isn.plans.flyscan import flyscan
import logging

logger = logging.getLogger(__name__)
sample = oregistry["sample"]
me7 = oregistry["me7"]
ptycho = oregistry["ptycho"]
tmm = oregistry["tetramm1"]
socketserver = oregistry["socketserver"]
savedata = oregistry["savedata"]

XSP3_MAX_PTS = 1000000

def fly2d(
    samplename: str = "smp1",
    user_comments: str = "",
    x_center: float = None,
    y_center: float = None,
    width: float = 0,
    height: float = 0,
    stepsize_x: float = 0.1,
    stepsize_y: float = 0.1,
    dwell_ms: float = 0,
    num_interferometer_per_pixel: int = 5,
    det_dead_ms: float = 0.01,
    xrf_on: bool = True,
    tmm_on: bool = True,
    ptycho_on: bool = False,
):

    """
    2D Bluesky plan that drives the x- and y- sample motors in flying mode
    The plan will drive samx and samy to the requested x_center and y_center, 
    and then perform a relative scan in the x and y directions.

    Parameters
    ----------
    samplename: 
        The name of the sample. Type: str. Default: "smp1".
    x_center:
        The center of the scan in the x direction. Type: float. Default: None which uses the current position of samx
    y_center:
        The center of the scan in the y direction. Type: float. Default: None which uses the current position of samy
    width:
        The width of the scan in mm. Type: float. Default: 0.
    height:
        The height of the scan in mm. Type: float. Default: 0.
    stepsize_x:
        The step size in the x direction in um. Type: float. Default: 0.1.
    stepsize_y:
        The step size in the y direction in um. Type: float. Default: 0.1.
    dwell_ms:
        The dwell time in the scan in ms. Type: float. Default: 0.
    det_dead_ms:
        The detector dead time in the scan in ms. Type: float. Default: 0.01.
    xrf_on:
        Whether to collect XRF data. Type: bool. Default: True.
    ptycho_on:
        Whether to collect Ptycho data. Type: bool. Default: False.
    tmm_on:
        Whether to collect TMM data. Type: bool. Default: True.
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
    x_min = -width*1e3/2
    x_max = width*1e3/2
    y_min = -height*1e3/2 + y_piezo_center
    y_max = height*1e3/2 + y_piezo_center
    x_npts = int(width*1e3/stepsize_x)
    y_npts = int(height*1e3/stepsize_y)
    acquire_time = dwell_ms
    det_dead = det_dead_ms
    F = 0.9
    interferometer_frequency = int(1000 * num_interferometer_per_pixel / (dwell_ms + det_dead_ms))
    logger.info(f"Interferometer frequency set to {interferometer_frequency}")

    total_pts = x_npts * (y_npts / F)
    if total_pts >= XSP3_MAX_PTS:
        raise ValueError(f"Total points {total_pts} is greater than the maximum allowed {XSP3_MAX_PTS}")
    
    """Define the detectors"""
    dets = []
    if xrf_on:
        dets.append(me7)
    if ptycho_on:
        dets.append(ptycho)
    if tmm_on:
        dets.append(tmm)

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
        yield from flyscan(dets, **plan_args)
    yield from _fly2d()

    """Move sample y to the starting position"""
    yield from bps.mv(sample.y, y_center)

    """Write the master HDF5 file for the scan"""
    dets.append(socketserver)
    for d in dets:
        print(d.name)
    generate_scan_master_h5(bluesky_params=plan_args.update(initial_args), dets=dets)
    yield from bps.sleep(2)
    


    

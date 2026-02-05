"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    fly2d
""".split()

import logging
import bluesky.preprocessors as bpp
from mic_common.utils.param_capture import capture_params
from s2idd_uprobe.plans.flyscan_core import _fly2d_scanrecord
from apsbits.core.instrument_init import oregistry

logger = logging.getLogger(__name__)
savedata = oregistry["savedata"]
sample = oregistry["sample"]
# scanrecord = oregistry["scanrecord"]
# savedata = scanrecord.savedata

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
        The name of the sample for file naming. Default: "smp1". 
    user_comments:
        User comments to be recorded with the scan data. Default is "". 
    width:
        The total width of the scan area in microns. Default: 0. 
    x_center:
        The center position of the scan in the x-direction in microns. If not provided, 
        the current x-motor position will be used as the center. Default: None.
    stepsize_x:
        The step size (spatial resolution) in the x-direction in microns. Default: 0. 
    height:
        The total height of the scan area in microns. Default: 0. 
    y_center:
        The center position of the scan in the y-direction in microns. If not provided, 
        the current y-motor position will be used as the center. Default: None. 
    stepsize_y:
        The step size (spatial resolution) in the y-direction in microns. Default: 0. 
    dwell_ms:
        The dwell time per step in milliseconds. Default: 0. 
    sample_z:
        The sample z position in millimeters. If not provided, the current sample z 
        position will be maintained. Default: None. 
    xrf_on:
        Whether to enable the x-ray fluorescence detector. Default is True. 
    preamp1_on:
        Whether to enable preamp1. Preamp1 is used to record metadata. Default is True. 
    """


    
    """Capture the input plan parameters"""
    # Use the current motor positions if not provided
    x_center = round(sample.x.position, 2) if x_center is None else x_center
    y_center = round(sample.y.position, 2) if y_center is None else y_center
    sample_z = round(sample.z.position, 2) if sample_z is None else sample_z

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



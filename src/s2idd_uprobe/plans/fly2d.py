"""
Creating a bluesky fly2d plan that does not use Scan Record.

This module provides a 2D flyscan plan that performs raster scanning without relying on Scan Record.

Plan Description:
----------------
Execute a 2D flyscan over a rectangular area by performing multiple 1D flyscans along the x-axis
at different y positions. The scan follows this sequence:

1. Setup and validation of scan parameters and detector connections
2. Configure detector settings and file I/O based on scan parameters
3. Position the sample at the specified z-height and y-start position
4. For each y-position:
   a. Move y-motor to the target y-coordinate
   b. Execute a 1D flyscan along the x-axis
   c. Retrace x-motor to start position (unless snake_scan is enabled)
5. Continue until all y-positions are scanned

Scan Patterns:
--------------
- **Standard raster**: Always scans from left to right, retracing after each line
- **Snake scan**: Alternates scan direction (left-to-right, then right-to-left) to reduce scan time

Key Features:
-------------
- Automatic motor speed calculation based on step size and dwell time
- Detector synchronization for data integrity
- Configurable detector selection (XRF, preamp1, preamp2)
- Automatic file I/O configuration
- Support for both standard and snake scan patterns

@author: yluo(grace227)
"""

__all__ = """
    fly2d
""".split()

import logging
import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import oregistry
from s2idd_uprobe.utils.fly import validate_scan_parameters
from mic_common.utils.param_capture import capture_params
from s2idd_uprobe.plans.flyscan_core import _fly2d

logger = logging.getLogger(__name__)

savedata = oregistry["savedata"]
sample = oregistry["sample"]
# scanrecord = oregistry["scanrecord"]
# savedata = scanrecord.savedata

def fly2d(
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
    preamp1_on: bool = True,
    xrf_on: bool = True,
    snake_scan: bool = False,
):
    """
    Execute a 2D flyscan over a rectangular area without using Scan Record.

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
        The sample z position in millimeters. If not provided, the current sample z position
        will be used. Default: None. 
    xrf_on:
        Whether to enable the x-ray fluorescence detector. Default is True. 
    preamp1_on:
        Whether to enable preamp1. Preamp1 is used to record metadata. Default is True. 
    snake_scan:
        Whether to use snake scan pattern (alternating scan directions). 
        When False, standard raster scan. Default is False. 
    """

    """Capture the input plan parameters"""
    # Use the current motor positions if not provided. If provided, move the motor to the requested position.
    validate_scan_parameters(
        width=width, height=height, stepsize_x=stepsize_x, stepsize_y=stepsize_y, dwell_ms=dwell_ms
    )
    x_center = x_center if x_center is not None else (round(sample.x.position - width / 2, 2))
    y_center = y_center if y_center is not None else (round(sample.y.position - height / 2, 2))
    sample_z = sample_z if sample_z is not None else (round(sample.z.position, 2))

    plan_args = capture_params(fly2d, **locals())
    logger.info(f"Plan arguments: {plan_args}")

    scan_id = None
    try:
        scan_id = savedata.next_scan_number.get()
        logger.info(f"Scan id: {scan_id}")
    except Exception as e:
        logger.error(f"Error getting scan id: {e}")
        scan_id = None

    md = {"plan_args": plan_args, "scan_id": scan_id}

    @bpp.run_decorator(md=md)
    def _fly2d_wrapper():
        yield from _fly2d(**plan_args)

    yield from _fly2d_wrapper()

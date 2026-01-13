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
import numpy as np
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import oregistry
from s2idd_uprobe.utils.fly import get_next_file_name
from s2idd_uprobe.utils.param_capture import capture_params
from s2idd_uprobe.plans.flyscan_core import (
    _common_flyscan_setup,
    _common_flyscan_cleanup,
    _fly1d
)
from mic_common.utils.timer_decorator import loop_timer_context
# from mic_common.utils.param_capture import capture_params
from s2idd_uprobe.utils.nexus_bps_func import save_ophyd_value

logger = logging.getLogger(__name__)

savedata = oregistry["savedata"]
samx = oregistry["samx"]
samy = oregistry["samy"]
samz = oregistry["samz"]

def fly2d(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
    height=0,
    y_center=None,
    stepsize_y=0,
    dwell_ms=0,
    sample_z=None,
    inc_eng=None,
    adjust_zp=False,
    preamp2_on=False,
    preamp1_on=True,
    xrf_on=True,
    snake_scan=False,
):
    
    """
    Execute a 2D flyscan over a rectangular area without using Scan Record.
    
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
    height:
        The total height of the scan area in microns. Default: 0. Type: float
    y_center:
        The center position of the scan in the y-direction in microns. If not provided, the current y-motor position will be used as the center. Default: None. Type: float
    stepsize_y:
        The step size (spatial resolution) in the y-direction in microns. Default: 0. Type: float
    dwell_ms:
        The dwell time per step in milliseconds. Default: 0. Type: float
    sample_z:
        The sample z position in millimeters. If not provided, the current sample z position will be maintained. Default: None. Type: float
    inc_eng:
        The increment in energy (currently not implemented). Default: None. Type: float
    adjust_zp:
        Whether to adjust the zero point (currently not implemented). Default: False. Type: bool
    xrf_on:
        Whether to enable the x-ray fluorescence detector. Default is True. Type: bool
    preamp1_on:
        Whether to enable preamp1. Preamp1 is used to record metadata. Default is True. Type: bool
    preamp2_on:
        Whether to enable preamp2. Default is False. Type: bool
    snake_scan:
        Whether to use snake scan pattern (alternating scan directions). When False, standard raster scan. Default is False. Type: bool
    """

    """Capture the input plan parameters"""
    if x_center is None:
        x_center = samx.position
    if y_center is None:
        y_center = samy.position
    if sample_z is None:
        sample_z = samz.position
    plan_args = capture_params(fly2d, **locals())

    """Common setup for flyscan plans"""
    devices, fileplugins, xarr, x_start, x_end, x_motor_scan_speed, x_motor_retrace = yield from _common_flyscan_setup(
        xrf_on=xrf_on, 
        preamp1_on=preamp1_on, 
        preamp2_on=preamp2_on,
        x_center=x_center,
        width=width,
        height=height,
        stepsize_x=stepsize_x,
        stepsize_y=stepsize_y,
        dwell_ms=dwell_ms
    )
    
    """Setup the sample z, x, and y position"""
    if sample_z is not None:
        yield from bps.mv(samz, sample_z)
    if x_center is None:
        yield from bps.mv(samx, samx.position - width/2)
    if y_center is not None:
        yield from bps.mv(samy, samy.position - height/2)

    """Construct the y scan points"""
    yarr = np.arange(y_center - height/2, y_center + height/2, stepsize_y)
    
    # Drive the y-motor to the start position
    x_target = [x_end, x_start]
    filename = get_next_file_name(savedata)
    filename = filename.replace(".mda", "")

    md = {"plan_args": plan_args,
          "shape": (len(yarr), len(xarr)),
          "extents": [[x_start, x_end], [yarr[0], yarr[-1]]],
          }

    @bpp.run_decorator(md=md)
    def _fly2d():
        with loop_timer_context(f"Data saved to {filename}", total_iterations=len(yarr)) as timer:
            for i, y in enumerate(yarr):
                timer.iteration(i + 1, samy=y)
                yield from bps.mv(samy, y)
                yield from save_ophyd_value(samy)

                if i == 0:
                    print("Open shutter")
                    yield from savedata.set_next_scan_number(savedata.next_scan_number.get() + 1)
                
                if snake_scan:
                    x_target_pos = x_target[i%2]
                    yield from _fly1d(devices, fileplugins, samx, x_target_pos)
                else:
                    x_target_pos = x_end
                    yield from _fly1d(devices, fileplugins, samx, x_target_pos)
                    yield from bps.mv(samx.velocity, x_motor_retrace)
                    yield from bps.mv(samx, x_start)
                    yield from bps.mv(samx.velocity, x_motor_scan_speed)
                    logger.debug(f"x_motor velocity = {samx.velocity.get()}")
                timer.end_iteration()

    yield from _fly2d()
    
    """Common cleanup for flyscan plans"""
    yield from _common_flyscan_cleanup()

    
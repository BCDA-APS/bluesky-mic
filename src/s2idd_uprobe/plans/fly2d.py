"""
Creating a bluesky plan that does not use Scan Record.

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
from apsbits.core.instrument_init import oregistry
from s2idd_uprobe.utils.fly import get_next_file_name
from s2idd_uprobe.plans.flyscan_core import (
    _common_flyscan_setup,
    _common_flyscan_cleanup,
    _fly1d
)
from mic_common.utils.timer_decorator import loop_timer_context

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
    dwell=0,
    sample_z=None,
    inc_eng=None,
    adjust_zp=False,
    preamp2_on=False,
    preamp1_on=True,
    xrf_on=True,
    snake_scan=False,
):
    
    """
    Execute a 2D flyscan over a rectangular area.
    
    Parameters
    ----------
    samplename : str, optional
        The name of the sample for file naming. Default is "smp1".
    user_comments : str, optional
        User comments to be recorded with the scan data. Default is "".
    width : float
        The total width of the scan area in motor units.
    x_center : float, optional
        The center position of the scan in the x-direction. If not provided, 
        the current x-motor position will be used as the center.
    stepsize_x : float
        The step size (spatial resolution) in the x-direction in motor units.
    height : float
        The total height of the scan area in motor units.
    y_center : float, optional
        The center position of the scan in the y-direction. If not provided, 
        the current y-motor position will be used as the center.
    stepsize_y : float
        The step size (spatial resolution) in the y-direction in motor units.
    dwell : float
        The dwell time per step in milliseconds.
    sample_z : float, optional
        The sample z position. If not provided, the current sample z position 
        will be maintained.
    inc_eng : float, optional
        The increment in energy (currently not implemented).
    adjust_zp : bool, optional
        Whether to adjust the zero point (currently not implemented).
    xrf_on : bool, optional
        Whether to enable the x-ray fluorescence detector. Default is True.
    preamp1_on : bool, optional
        Whether to enable preamp1. Default is True. Preamp1 is used to record metadata.
    preamp2_on : bool, optional
        Whether to enable preamp2. Default is False.
    snake_scan : bool, optional
        Whether to use snake scan pattern (alternating scan directions). 
        Default is False (standard left-to-right raster).
    """

    """Common setup for flyscan plans"""
    devices, fileplugins, x_start, x_end, x_motor_scan_speed, x_motor_retrace = yield from _common_flyscan_setup(
        xrf_on=xrf_on, 
        preamp1_on=preamp1_on, 
        preamp2_on=preamp2_on,
        x_center=x_center,
        width=width,
        stepsize_x=stepsize_x,
        stepsize_y=stepsize_y,
        dwell=dwell
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

    with loop_timer_context(f"Data saved to {filename}", total_iterations=len(yarr)) as timer:
        for i, y in enumerate(yarr):
            timer.iteration(i + 1, samy=y)
            yield from bps.mv(samy, y)

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

    """Common cleanup for flyscan plans"""
    yield from _common_flyscan_cleanup()

    
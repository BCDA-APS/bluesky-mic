"""
Fly1D plan for 2idd. A building block for fly2d_noScanRecord plan.

This module provides a 1D flyscan plan that performs continuous motion scanning along the x-axis
without relying on Scan Record.

Plan Description:
----------------
Execute a 1D flyscan where the x-motor moves at a calculated speed while detectors continuously 
capture data. The scan follows this sequence:

1. Setup and validation of scan parameters and detector connections
2. Configure detector settings and file I/O based on scan parameters
3. Position the x-motor at the start position and set scan speed
4. Execute the scan by moving the x-motor to the end position
5. Wait for all detector data to be captured and saved
6. Retrace the x-motor to the start position at high speed
7. Restore motor speed to scan speed for potential subsequent scans

Key Features:
-------------
- Automatic motor speed calculation based on step size and dwell time
- Detector synchronization for data integrity
- Configurable detector selection (XRF, preamp1, preamp2)
- Automatic file I/O configuration
- Motor speed optimization for scan and retrace operations

@author: yluo(grace227)
"""

import bluesky.plan_stubs as bps
from apsbits.core.instrument_init import oregistry
from s2idd_uprobe.plans.flyscan_core import (
    _common_flyscan_setup,
    _common_flyscan_cleanup,
    _fly1d,
)
from s2idd_uprobe.utils.fly import get_next_file_name

import logging

logger = logging.getLogger(__name__)

savedata = oregistry["savedata"]
samx = oregistry["samx"]

def fly1d(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
    dwell=0,
    sample_z=None,
    xrf_on=True,
    preamp1_on=False,
    preamp2_on=False,
):
    """
    Execute a 1D flyscan along the x-axis.
    
    See module header for detailed description of the scan process and features.
    
    Parameters
    ----------
    samplename : str, optional
        The name of the sample for file naming. Default is "smp1".
    user_comments : str, optional
        User comments to be recorded with the scan data. Default is "".
    width : float
        The total width of the scan in motor units.
    x_center : float, optional
        The center position of the scan in the x-direction. If not provided, 
        the current x-motor position will be used as the center.
    stepsize_x : float
        The step size (spatial resolution) of the scan in motor units.
    dwell : float
        The dwell time per step in milliseconds.
    sample_z : float, optional
        The sample z position. If not provided, the current sample z position 
        will be maintained.
    xrf_on : bool, optional
        Whether to enable the x-ray fluorescence detector. Default is True.
    preamp1_on : bool, optional
        Whether to enable preamp1. Default is False.
    preamp2_on : bool, optional
        Whether to enable preamp2. Default is False.
    """

    #TODO: open shutter
    print("open shutter")

    """Common setup for flyscan plans"""
    devices, fileplugins, x_start, x_end, x_motor_scan_speed, x_motor_retrace = yield from _common_flyscan_setup(
        xrf_on=xrf_on, 
        preamp1_on=preamp1_on, 
        preamp2_on=preamp2_on,
        x_center=x_center,
        width=width,
        stepsize_x=stepsize_x,
        dwell=dwell
    )
    
    """Execute the fly1d scan"""
    filename = get_next_file_name(savedata)
    logger.info(f"Starting the scan, filename: {filename}")
    yield from savedata.set_next_scan_number(savedata.next_scan_number.get() + 1)
    yield from _fly1d(devices, fileplugins, samx, x_end)
    yield from bps.mv(samx.velocity, x_motor_retrace)
    yield from bps.mv(samx, x_start)
    yield from bps.mv(samx.velocity, x_motor_scan_speed)
    logger.info(f"Scan is finished, filename: {filename}")

    """Common cleanup for flyscan plans"""
    yield from _common_flyscan_cleanup()






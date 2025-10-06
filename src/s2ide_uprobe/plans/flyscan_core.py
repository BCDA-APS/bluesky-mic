"""
Common functionality for flyscan plans (fly1d and fly2d).

This module provides shared functions and utilities that are used by both fly1d and fly2d
flyscan plans, eliminating code duplication and providing a centralized location for
common operations.

Functions:
----------
_common_flyscan_setup(xrf_on, preamp1_on, preamp2_on, x_center, width, stepsize_x, 
                      stepsize_y, dwell)
    Common setup function that handles parameter validation, device connections,
    detector configuration, and motor setup for both 1D and 2D flyscans.

_common_flyscan_cleanup()
    Common cleanup function that re-enables usercalc after scan completion.

_fly1d(devices, fileplugins, samx, x_end)
    Core detector execution function used by both fly1d and fly2d plans.
    Handles detector synchronization and data capture during the scan.

Key Features:
-------------
- Centralized parameter validation and device connection checking
- Automatic detector setup and file I/O configuration
- Motor speed calculation and positioning
- Device reordering for optimal scan execution
- Detector status monitoring and synchronization

@author: yluo(grace227)
"""

import bluesky.plan_stubs as bps
from apsbits.core.instrument_init import oregistry
from apstools.plans import run_blocking_function
from s2ide_uprobe.plans.toggle_usercalc import enable_usercalc, disable_usercalc
from s2idd_uprobe.utils.fly import (
    reorder_devices,
    validate_scan_parameters,
    validate_device_connections,
    setup_detectors_and_fileio,
    setup_motor_positions_and_speeds,
    calculate_x_scan_parameters,
    DetectorFileSignal
)
from s2idd_uprobe.utils.nexus_bps_func import save_ophyd_value
import logging

logger = logging.getLogger(__name__)

savedata = oregistry["savedata"]
samx = oregistry["samx"]
usercalc_xmap_filename = oregistry["usercalc_xmap_filename"]


def _common_flyscan_setup(
    xrf_on=True, 
    ptycho_on=False,
    preamp_on=False,
    x_center=None,
    width=0,
    stepsize_x=0,
    stepsize_y=None,
    dwell=0
):
    """
    Common setup for both fly1d and fly2d plans.
    
    Parameters
    ----------
    xrf_on : bool
        Whether x-ray fluorescence is on
    preamp_on : bool
        Whether preamp is on
    x_center : float, optional
        Center of scan in x direction
    width : float
        Width of scan
    stepsize_x : float
        Step size in x direction
    stepsize_y : float, optional
        Step size in y direction (for 2D scans)
    dwell : float
        Dwell time
        
    Returns
    -------
    tuple
        (devices, fileplugins, xarr, x_start, x_end, x_motor_scan_speed, x_motor_retrace, num_pulses)
    """
    
    """Disable usercalc"""
    usercalc_xmap_filename.set(0)

    """Check input parameters and detector status"""
    logger.info("Validating scan parameters and detector status")
    validate_scan_parameters(stepsize_x=stepsize_x, stepsize_y=stepsize_y)
    devices, fileplugins = validate_device_connections(xrf_on, preamp_on, ptycho_on, return_devices=True)

    """Construct the scan points and calculate the motor speeds"""
    logger.info("Constructing the scan points and calculating the motor speeds")
    xarr, x_start, x_end, x_motor_scan_speed, x_motor_retrace, num_pulses = calculate_x_scan_parameters(
        width, x_center, stepsize_x, dwell
    )
    logger.info(f"x_start: {x_start}, x_end: {x_end}, x_motor_scan_speed: {x_motor_scan_speed}, num_pulses: {num_pulses}")

    """Setup detectors and file I/O"""
    logger.info("Setting up detectors and file I/O")
    numpts_x = len(xarr)
    num_pulses = numpts_x - 2
    yield from setup_detectors_and_fileio(stepsize_x, num_pulses, samx.resolution.get(), dwell,
                                          xrf_on=xrf_on, preamp1_on=preamp1_on, preamp2_on=preamp2_on)
        
    """Setup motor positions and speeds"""
    yield from setup_motor_positions_and_speeds(x_start, x_motor_scan_speed, x_motor_retrace)
    
    """Lets move the sis3820 device to the end of the list of devices"""
    devices = reorder_devices(devices)
    
    return devices, fileplugins, xarr, x_start, x_end, x_motor_scan_speed, x_motor_retrace


def _common_flyscan_cleanup():
    """
    Common cleanup for both fly1d and fly2d plans.
    """
    """Enable usercalc"""
    yield from enable_usercalc()


def _fly1d(devices, fileplugins, samx, x_end):
    """
    This function is being used in both fly1d and fly2d plans.
    
    Parameters
    ----------
    devices : list
        List of ophyd devices
    fileplugins : list
        List of file plugins
    samx : ophyd.Device
        Sample x motor
    x_end : float
        End position for x motor
    """
    status = DetectorFileSignal(fileplugins, devices)
    
    for fileplugin in fileplugins:
        if fileplugin is not None:
            yield from fileplugin.set_capture("CAPTURING")

    for det in devices:
        if det.name == "sis3820":
            yield from det.set_erase_start(1)
        elif det.name == "xrf":
            yield from det.set_erase_start(1)
        elif det.name == "tmm1":
            yield from det.start_acquire()
        elif det.name == "tmm2":
            yield from det.start_acquire()

    yield from bps.sleep(0.2)
    status.scan_active = True
    logger.debug(f"scan_active: {status.scan_active}")
    yield from save_ophyd_value(samx)
    yield from bps.mv(samx, x_end)
    yield from save_ophyd_value(samx)
    yield from bps.sleep(0.2)
    yield from run_blocking_function(status.st.wait)
    status.unsubscribe()






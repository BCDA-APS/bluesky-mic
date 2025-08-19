"""
Core functions for flyscan plans.

@author: yluo(grace227)
"""

import logging
import bluesky.plan_stubs as bps
from apsbits.core.instrument_init import oregistry
from apsbits.utils.config_loaders import get_config
import numpy as np
from ophyd.status import Status

logger = logging.getLogger(__name__)

# Get common devices and config
sis3820 = oregistry["sis3820"]
savedata = oregistry["savedata"]
xrf = oregistry["xrf"]
xrf_netcdf = oregistry["xrf_netcdf"]
samx = oregistry["samx"]

iconfig = get_config()
netcdf_delimiter = iconfig.get("FILE_DELIMITER")
xmap_buffer = iconfig.get("XMAP")["BUFFER"]
det_foldername = {"xrf": "flyXRF", "preamp1": "tetramm", "preamp2": "tetramm2"}


def setup_flyscan_SIS3820_XMAP(sis3820, xmap, stepsize_x, num_pulses, motor_resolution):
    """
    Setup the SIS3820 and XMAP for the fly scan.

    """
    yield from sis3820.before_flyscan(num_pulses, stepsize=stepsize_x, 
                                      motor_resolution=motor_resolution,
                                      update_prescale=True)
    yield from xmap.flyscan_before(num_pulses)


def setup_detectors_and_fileio(stepsize_x, num_pulses, motor_resolution):
    """
    Common setup for SIS3820, XMAP, and XRF netCDF file writer.
    
    Parameters
    ----------
    stepsize_x : float
        Step size in x direction
    num_pulses : int
        Number of pulses for the scan
    motor_resolution : float
        Motor resolution for prescale calculation
        
    Returns
    -------
    str
        Filename for the scan
    """
    # Update file name
    savedata.update_next_file_name()
    next_file_name = savedata.next_file_name
    filename = next_file_name.replace(".mda", "")
    
    # Setup the SIS3820 and XMAP (XRF)
    yield from setup_flyscan_SIS3820_XMAP(sis3820, xrf, stepsize_x, 
                                        num_pulses, motor_resolution)
    
    # Setup the XRF netCDF
    num_capture = int(np.ceil(num_pulses / xmap_buffer))
    
    yield from xrf_netcdf.setup_file_writer(
        savedata,
        det_foldername["xrf"],
        num_capture,
        filename=filename,
        beamline_delimiter=netcdf_delimiter,
    )
    
    return filename


def setup_motor_positions_and_speeds(x_start, x_motor_scan_speed, x_motor_retrace):
    """
    Common setup for motor positions and speeds.
    
    Parameters
    ----------
    x_start : float
        Starting x position
    x_motor_scan_speed : float
        Scan speed for x motor
    x_motor_retrace : float
        Retrace speed for x motor
    """
    yield from bps.mv(samx.velocity, x_motor_retrace)
    yield from bps.mv(samx, x_start)
    yield from bps.mv(samx.velocity, x_motor_scan_speed)
    yield from bps.sleep(0.2)
    logger.info(f"x_motor velocity = {samx.velocity.get()}")


def create_file_done_signal():
    """
    Create a Status object and subscribe to file done signal.
    
    Returns
    -------
    Status
        Status object that will be finished when file is done
    """
    ready = Status()
    
    def wait(old_value, value, **kwargs):
        if old_value == 1 and value == 0:
            if not ready.done:
                ready.set_finished()
            else:
                logger.info("File done signal already received")
    
    xrf_netcdf.capture.unsubscribe_all()
    xrf_netcdf.capture.subscribe(wait)
    
    return ready


def calculate_x_scan_parameters(width, x_center, stepsize_x, dwell):
    """
    Calculate common scan parameters.
    
    Parameters
    ----------
    width : float
        Width of the scan
    x_center : float
        Center of the scan in x direction
    stepsize_x : float
        Step size in x direction
    dwell : float
        Dwell time
        
    Returns
    -------
    tuple
        (xarr, x_start, x_end, x_motor_scan_speed, x_motor_retrace, num_pulses)
    """
    xarr = np.arange(x_center - width/2, x_center + width/2, stepsize_x)
    x_motor_scan_speed = samx.calculate_scan_speed(stepsize_x, dwell)
    x_motor_retrace = samx.get_max_velocity()
    num_pulses = len(xarr) - 2
    
    x_start = xarr[0]
    x_end = xarr[-1]
    
    return xarr, x_start, x_end, x_motor_scan_speed, x_motor_retrace, num_pulses


def validate_scan_parameters(stepsize_x, stepsize_y):
    """
    Validate common scan parameters.
    
    Parameters
    ----------
    stepsize_x : float
        Step size in x direction
    stepsize_y : float
        Step size in y direction
        
    Raises
    ------
    ValueError
        If step sizes are invalid
    """
    if any([stepsize_y == 0, stepsize_x == 0]):
        raise ValueError("Step size cannot be 0, please check the input parameters")


def validate_device_connections():
    """
    Validate that required devices are connected.
    
    Raises
    ------
    ValueError
        If any required device is not connected
    """
    devices = [sis3820, xrf, xrf_netcdf]
    for device in devices:
        if not device.connected:
            raise ValueError(f"{device.name} is not connected, please check the status")

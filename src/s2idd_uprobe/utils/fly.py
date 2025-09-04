"""
Core functions for flyscan plans.

This module contains utility functions and classes that support flyscan operations,
including detector setup, motor control, parameter validation, and status monitoring.

Functions:
----------
get_next_file_name(savedata)
    Generate the next filename for scan data files.

setup_detectors_and_fileio(stepsize_x, num_pulses, motor_resolution, dwell_time, 
                          xrf_on=True, preamp1_on=True, preamp2_on=False)
    Configure all detectors and file I/O for flyscan operations.

setup_motor_positions_and_speeds(x_start, x_motor_scan_speed, x_motor_retrace)
    Position the x-motor and set appropriate scan and retrace speeds.

calculate_x_scan_parameters(width, x_center, stepsize_x, dwell)
    Calculate scan parameters including motor speeds and scan points.

validate_scan_parameters(stepsize_x=None, stepsize_y=None, width=None, height=None, dwell_ms=None)
    Validate that step sizes, width, height, and dwell time are non-zero and valid.

validate_device_connections(xrf_on, preamp1_on, preamp2_on, return_devices=False)
    Validate that required devices are connected and return device lists.

reorder_devices(devices)
    Reorder device list to put sis3820 at the end for proper scan execution.

Classes:
--------
DetectorFileSignal(fileplugins, devices)
    Monitor the status of fileplugins and detectors during scans.
    Provides synchronization for scan completion.

@author: yluo(grace227)
"""

import logging
import bluesky.plan_stubs as bps
from apsbits.core.instrument_init import oregistry
from apsbits.utils.config_loaders import get_config
import numpy as np
from ophyd.status import Status

logger = logging.getLogger(__name__)

iconfig = get_config()
netcdf_delimiter = iconfig.get("FILE_DELIMITER")
xmap_buffer = iconfig.get("XMAP")["BUFFER"]
det_foldername = {"xrf": "flyXRF", "tmm1": "tetramm1", "tmm2": "tetramm2"}


def get_next_file_name(savedata):
    """
    Get the next file name for the scan.

    Parameters
    ----------
    savedata : ophyd.Device
        Savedata device

    Returns
    -------
    str
        Next file name
    """
    
    # Update file name
    savedata.update_next_file_name()
    next_file_name = savedata.next_file_name
    filename = next_file_name.replace(".mda", "")

    return filename


def setup_detectors_and_fileio(stepsize_x, num_pulses, motor_resolution, dwell_time,
                               devices, fileplugins):
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
    dwell_time : float
        Dwell time for the scan in ms
    devices : list
        List of ophyd devices
    fileplugins : list
        List of ophyd fileplugins
    Returns
    -------
    str
        Filename for the scan
    """
    
    # Get the next file name
    savedata = oregistry["savedata"]
    filename = get_next_file_name(savedata)

    # Setup detector and fileio
    for det, fileplugin in zip(devices, fileplugins):
        if det.name == "sis3820":
            yield from det.before_flyscan(num_pulses, stepsize=stepsize_x, 
                                      motor_resolution=motor_resolution,
                                      update_prescale=True)
        elif det.name == "xrf":
            yield from det.before_flyscan(num_pulses)
            # Setup the XRF netCDF
            num_capture = int(np.ceil(num_pulses / xmap_buffer))

        elif det.name == "tmm1":
            yield from det.before_flyscan(num_pulses, dwell_time)
            num_capture = num_pulses

        elif det.name == "tmm2":
            yield from det.before_flyscan(num_pulses, dwell_time)
            num_capture = num_pulses

        # Setup fileio
        if fileplugin is not None:
            yield from fileplugin.setup_file_writer(
                savedata,
                det_foldername[det.name],
                num_capture,
                filename=filename,
                beamline_delimiter=netcdf_delimiter,
            )
            logger.info(f"Setup fileIO for {det.name}")


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

    samx = oregistry["samx"]

    yield from bps.mv(samx.velocity, x_motor_retrace)
    yield from bps.mv(samx, x_start)
    yield from bps.mv(samx.velocity, x_motor_scan_speed)
    yield from bps.sleep(0.2)
    logger.info(f"x_motor velocity = {samx.velocity.get()}")


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
    samx = oregistry["samx"]
    xarr = np.arange(x_center - width/2, x_center + width/2, stepsize_x)
    x_motor_scan_speed = samx.calculate_scan_speed(stepsize_x, dwell)
    x_motor_retrace = samx.get_max_velocity()
    num_pulses = len(xarr) - 2
    
    x_start = xarr[0]
    x_end = xarr[-1]
    
    return xarr, x_start, x_end, x_motor_scan_speed, x_motor_retrace, num_pulses


def validate_scan_parameters(stepsize_x=None, stepsize_y=None, width=None, height=None, dwell_ms=None):
    """
    Validate common scan parameters.
    
    Parameters
    ----------
    stepsize_x : float
        Step size in x direction
    stepsize_y : float
        Step size in y direction
    width : float
        Width of the scan
    height : float
        Height of the scan
    dwell_ms : float
        Dwell time in ms

    Raises
    ------
    ValueError
        If step sizes are invalid
    """
    if stepsize_x is not None and stepsize_x == 0: 
        raise ValueError("Step size cannot be 0, please check the input parameters")
    if stepsize_y is not None and stepsize_y == 0:
        raise ValueError("Step size cannot be 0, please check the input parameters")
    if width is not None and width == 0:
        raise ValueError("Width cannot be 0, please check the input parameters")
    if height is not None and height == 0:
        raise ValueError("Height cannot be 0, please check the input parameters")
    if dwell_ms is not None and dwell_ms == 0:
        raise ValueError("Dwell time cannot be 0, please check the input parameters")

def validate_device_connections(xrf_on, preamp1_on, preamp2_on, return_devices=False):
    """
    Validate that required devices are connected.
    
    Raises
    ------
    ValueError
        If any required device is not connected
    """
    sis3820 = oregistry["sis3820"]
    devices = [sis3820]

    fileplugins = [None]
    if xrf_on:
        try:
            xrf = oregistry["xrf"]
            xrf_netcdf = oregistry["xrf_netcdf"]
            devices.append(xrf)
            fileplugins.append(xrf_netcdf)
        except KeyError:
            logger.warning(f"Either {xrf.prefix} or {xrf_netcdf.prefix} is not connected, please check the status")
    if preamp1_on:
        try:
            tmm1 = oregistry["tmm1"]
            tmm1_hdf = oregistry["tmm1_hdf"]
            devices.append(tmm1)
            fileplugins.append(tmm1_hdf)
        except KeyError:
            logger.warning(f"Either {tmm1.prefix} or {tmm1_hdf.prefix} is not connected, please check the status")
    if preamp2_on:
        try:
            tmm2 = oregistry["tmm2"]
            tmm2_hdf = oregistry["tmm2_hdf"]
            devices.append(tmm2)
            fileplugins.append(tmm2_hdf)
        except KeyError:
            logger.warning(f"Either {tmm2.prefix} or {tmm2_hdf.prefix} is not connected, please check the status")

    for device in devices:
        if not device.connected:
            raise ValueError(f"{device.name} is not connected, please check the status")
    
    for fileplugin in fileplugins:
        if fileplugin is not None and not fileplugin.connected:
            raise ValueError(f"{fileplugin.name} is not connected, please check the status")

    if return_devices:
        return devices, fileplugins


def reorder_devices(devices):
    """
    Reorder the devices to put sis3820 at the end of the list.

    Parameters
    ----------
    devices : list
        List of ophyd devices

    Returns
    -------
    list
        List of ophyd devices with sis3820 at the end
    """

    device_names = [det.name for det in devices]
    sis3820_index = device_names.index("sis3820")
    devices.append(devices.pop(sis3820_index))

    return devices


class DetectorFileSignal:
    """
    Create a DetectorFileSignal object to monitor the status of the fileplugins and detectors.
    This class takes ophyd devices and fileplugins as input, and will subscribe to a single callback function named 
    update_status. The update_status function will be called when the status of the ophyd devices or fileplugins changes.
    The update_status function will check the status of all other ophyd devices or fileplugins, and update the overall status of the DetectorFileSignal object.
    The overall status of the DetectorFileSignal object will be finished when all ophyd devices or fileplugins are done.

    Parameters
    ----------
    fileplugins : list
        List of ophyd FilePlugin objects
    devices : list
        List of ophyd devices

    Returns
    -------
    DetectorFileSignal
        DetectorFileSignal object that will be finished when all ophyd devices or fileplugins are done
    """

    def __init__(self, fileplugins, devices, subscribe_fileplugins=True):
        
        self.fileplugins = fileplugins
        self.devices = devices
        self.ophyd_status = {}
        self.st = Status()
        self.scan_active = False

        if subscribe_fileplugins:
            for fileplugin in self.fileplugins:
                if fileplugin is not None:
                    self.ophyd_status.update({fileplugin.name: {'status':False, 'ophyd_obj':fileplugin}})
                    fileplugin.capture.unsubscribe_all()
                    fileplugin.capture.subscribe(self.update_status)

        for det in self.devices:
            if det is not None:
                if det.name == "tmm1":
                    self.ophyd_status.update({det.name: {'status':False, 'ophyd_obj':det}})
                    det.acquire.unsubscribe_all()
                    det.acquire.subscribe(self.update_status)
                elif det.name == "tmm2":
                    self.ophyd_status.update({det.name: {'status':False, 'ophyd_obj':det}})
                    det.acquire.unsubscribe_all()
                    det.acquire.subscribe(self.update_status)
    

    def update_status(self, old_value, value, **kwargs):
        ophyd_name = kwargs['obj'].parent.name
        logger.debug(f"ophyd_name: {ophyd_name}, scan_active: {self.scan_active}")

        if self.scan_active:
            self.ophyd_status[ophyd_name]['status'] = True
            logger.debug(f"ophyd_name: {ophyd_name}, status: {self.ophyd_status[ophyd_name]['status']}")

            all_status = []
            for _, v in self.ophyd_status.items():
                all_status.append(v['status'])
            logger.debug(f"all_status: {all_status}")

            if all(all_status):
                self.st.set_finished()
                self.scan_active = False
                logger.debug(f"Scan is finished")
            else:
                for k, v in self.ophyd_status.items():
                    if not v['status']:
                        logger.debug(f"{k} is not done")
                        

    def unsubscribe(self):
        for fileplugin in self.fileplugins:
            if fileplugin is not None:
                fileplugin.capture.unsubscribe_all()
        for det in self.devices:
            if det is not None:
                if det.name == "sis3820":
                    det.erase_start.unsubscribe_all()
                elif det.name == "xrf":
                    det.erase_start.unsubscribe_all()
                elif det.name == "tmm1":
                    det.acquire.unsubscribe_all()
                elif det.name == "tmm2":
                    det.acquire.unsubscribe_all()
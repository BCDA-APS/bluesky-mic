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
from ophyd import Device

logger = logging.getLogger(__name__)


def setup_detectors_and_fileio(
        devices, 
        num_pulses:int = None, 
        dwell_time:float = None, 
        stepsize: float = None, 
        motor_resolution: float = None,
):
    """
    Setup the detectors and file I/O for the flyscan plan.
    
    Parameters
    ----------
    devices : list
        List of ophyd devices
    num_pulses : int
        Number of pulses for the scan
    dwell_time : float
        Dwell time for the scan in ms
    stepsize : float
        Step size for the scan in x direction
    motor_resolution : float
        Motor resolution for the scan
    """

    sample = oregistry["sample"]
    if motor_resolution is None:
        try:
            motor_resolution = sample.x.resolution.get()
        except AttributeError:
            raise ValueError("Motor resolution is not set, please check the connectivity of the sample x motor")

    for det in devices:
        det.config_flyscan(
            num_pulses=num_pulses,
            dwell_time=dwell_time,
            stepsize=stepsize,
            motor_resolution=motor_resolution,
        )
        det.stage()

def setup_motor_positions_and_speeds(x_start):
    """
    Common setup for motor positions and speeds.

    Parameters
    ----------
    x_start : float
        Starting x position
    """

    sample = oregistry["sample"]
    sample.x.set_speed()
    yield from bps.mv(sample.x, x_start)
    sample.x.set_speed(sample.x.scan_speed)
    yield from bps.sleep(0.2)
    logger.info(f"x_motor velocity = {sample.x.velocity.get()}")


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
    sample = oregistry["sample"]
    xarr = np.arange(x_center - width / 2, x_center + width / 2, stepsize_x)
    x_motor_scan_speed = sample.x.calculate_scan_speed(stepsize_x, dwell)
    sample.x.scan_speed = x_motor_scan_speed
    x_motor_retrace = sample.x.get_max_velocity()
    num_pulses = len(xarr) - 2

    x_start = xarr[0]
    x_end = xarr[-1]

    return xarr, x_start, x_end, x_motor_scan_speed, x_motor_retrace, num_pulses


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
    devices : list
        List of ophyd devices
    subscribe_fileplugins : bool
        Whether to subscribe to the fileplugins

    Returns
    -------
    DetectorFileSignal
        DetectorFileSignal object that will be finished when all ophyd devices or fileplugins are done
    """

    def __init__(self, devices, subscribe_fileplugins=True):

        self.devices = devices
        self.fileplugins = []
        self.ophyd_status = {}
        self.st = Status()
        self.scan_active = False

        if subscribe_fileplugins:
            for det in self.devices:
                fileplugin = getattr(det, 'fileplugin', None)
                if fileplugin is not None:
                    self.ophyd_status.update({fileplugin.name: {"status": False, "ophyd_obj": fileplugin}})
                    fileplugin.capture.unsubscribe_all()
                    fileplugin.capture.subscribe(self.update_status)
                    self.fileplugins.append(fileplugin)
                
        # for det in self.devices:
        #     if det is not None:
        #         if det.name == "tmm1":
        #             self.ophyd_status.update({det.name: {"status": False, "ophyd_obj": det}})
        #             det.acquire.unsubscribe_all()
        #             det.acquire.subscribe(self.update_status)
        #         elif det.name == "tmm2":
        #             self.ophyd_status.update({det.name: {"status": False, "ophyd_obj": det}})
        #             det.acquire.unsubscribe_all()
        #             det.acquire.subscribe(self.update_status)

    def update_status(self, old_value, value, **kwargs):
        ophyd_name = kwargs["obj"].parent.name
        logger.debug(f"ophyd_name: {ophyd_name}, scan_active: {self.scan_active}")

        if self.scan_active:
            self.ophyd_status[ophyd_name]["status"] = True
            logger.debug(f"ophyd_name: {ophyd_name}, status: {self.ophyd_status[ophyd_name]['status']}")

            all_status = []
            for _, v in self.ophyd_status.items():
                all_status.append(v["status"])
            logger.debug(f"all_status: {all_status}")

            if all(all_status):
                self.st.set_finished()
                self.scan_active = False
                logger.debug(f"Scan is finished")
            else:
                for k, v in self.ophyd_status.items():
                    if not v["status"]:
                        logger.debug(f"{k} is not done")

    def unsubscribe(self):
        if len(self.fileplugins) == 0:
            logger.debug(f"No fileplugins found and nothing to unsubscribe")
            return
        for fileplugin in self.fileplugins:
            fileplugin.capture.unsubscribe_all()

        # for det in self.devices:
        #     if det is not None:
        #         if det.name == "sis3820":
        #             det.erase_start.unsubscribe_all()
        #         elif det.name == "xrf":
        #             det.erase_start.unsubscribe_all()
        #         elif det.name == "tmm1":
        #             det.acquire.unsubscribe_all()
        #         elif det.name == "tmm2":
        #             det.acquire.unsubscribe_all()

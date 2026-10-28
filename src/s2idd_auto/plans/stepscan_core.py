"""
Common functionality for stepscan plans (step1d and step2d).

This module provides shared functions and utilities that are used by both step1d and step2d
stepscan plans, eliminating code duplication and providing a centralized location for
common operations.

Functions:
----------
_common_stepscan_setup(xrf_on, preamp1_on, preamp2_on, total_pts, dwell_ms, filename)
    Common setup function that handles detector configuration and file I/O setup.

_step1d(xrf, sis3820, pos_ophyd, pos_arr, timer, 
         y_index=None, numpts_x=None, y_pos=None)
    Core detector execution function used by both step1d and step2d plans.
    Handles detector synchronization and data capture during the scan.

_common_stepscan_cleanup(devices_dict)
    Common cleanup function that handles scan completion tasks for both step1d and step2d plans.

Key Features:
-------------
- Centralized detector and file I/O setup for stepscans
- Centralized detector execution logic for stepscans
- Automatic detector synchronization and status monitoring
- XRF acquisition waiting and status management
- Consistent timer integration for both 1D and 2D scans
- Common cleanup operations for scan completion

@author: yluo(grace227)
"""

import bluesky.plan_stubs as bps
from apstools.plans import run_blocking_function
from ophyd.status import Status
from apsbits.core.instrument_init import oregistry
from apsbits.utils.config_loaders import get_config
from s2idd_uprobe.utils.fly import validate_device_connections
import logging
from s2idd_uprobe.utils.nexus_bps_func import save_ophyd_value
from s2idd_uprobe.utils.fly import DetectorFileSignal
import numpy as np

logger = logging.getLogger(__name__)

savedata = oregistry["savedata"]
iconfig = get_config()
netcdf_delimiter = iconfig.get("FILE_DELIMITER")
xmap_buffer = iconfig.get("XMAP")["BUFFER"]
det_foldername = {"xrf": "flyXRF", "tmm1": "tetramm1", "tmm2": "tetramm2"}


def _common_stepscan_setup(xrf_on, preamp1_on, preamp2_on, num_pts, dwell_ms, filename):
    """
    Common setup function that handles detector configuration and file I/O setup.

    Parameters
    ----------
    xrf_on : bool
        Whether x-ray fluorescence is on
    preamp1_on : bool
        Whether preamp1 is on
    preamp2_on : bool
        Whether preamp2 is on
    num_pts : int
        Number of scan points
    dwell_ms : float
        Dwell time in milliseconds
    filename : str
        Filename for the scan

    Returns
    -------
    tuple
        (devices_dict, fileplugins_dict) - devices and fileplugins as dicts with device names as keys
    """
    # Check input parameters and detector status. Turn off xrf_netcdf file plugin
    logger.info("Validating scan parameters and detector status")
    devices, fileplugins = validate_device_connections(
        xrf_on, preamp1_on, preamp2_on, return_devices=True
    )
    # fileplugins2 = [None if plugin is not None and plugin.name == "xrf_netcdf" else plugin for plugin in fileplugins]

    # Setup detectors and file I/O
    logger.info("Setting up detectors and file I/O")
    devices_dict = {}
    fileplugins_dict = {}

    for det, fileplugin in zip(devices, fileplugins):
        devices_dict[det.name] = det
        fileplugins_dict[det.name] = fileplugin

        if det.name == "sis3820":
            yield from det.before_stepscan(num_pts)
            # yield from det.set_erase_start(1)
            num_capture = num_pts
        elif det.name == "tmm1":
            yield from det.before_flyscan(num_pts, dwell_ms)
            # yield from det.start_acquire()
            num_capture = num_pts
        elif det.name == "xrf":
            yield from det.before_stepscan(dwell_ms)
            num_capture = int(np.ceil(num_pts / xmap_buffer))
        else:
            raise ValueError(f"Detector {det.name} not supported")

        # Setup fileio
        if fileplugin is not None:
            yield from fileplugin.setup_file_writer(
                savedata,
                det_foldername[det.name],
                num_capture,
                filename=filename,
                beamline_delimiter=netcdf_delimiter,
            )
            # yield from fileplugin.set_capture("CAPTURING")
            logger.info(f"Setup fileIO for {det.name}")

    return devices_dict, fileplugins_dict


def _step1d(xrf, sis3820, pos_ophyd, pos_arr, timer, timer_motor_list, y_index=None):
    """
    Core detector execution function used by both step1d and step2d plans.
    Handles detector synchronization and data capture during the scan.

    Parameters
    ----------
    xrf : ophyd.Device
        XRF detector device
    sis3820 : ophyd.Device
        SIS3820 detector device
    pos_ophyd : ophyd.Device
        Positioner device (samx, samy, or samz)
    pos_arr : numpy.ndarray
        Array of positions to scan
    timer : loop_timer_context
        Timer context for tracking scan progress
    timer_motor_list : list
        List of ophyd motor devices to track in the timer
    y_index : int, optional
        Y index for 2D scans (used for timer iteration calculation)

    Yields
    ------
    Various bluesky plan operations
    """
    num_pts = len(pos_arr)
    for j, pos in enumerate(pos_arr):
        # Handle timer iteration for both 1D and 2D scans
        if y_index is not None:
            # 2D scan context
            timer.iteration(y_index * num_pts + j + 1, motorlist=timer_motor_list)
        else:
            # 1D scan context
            timer.iteration(j + 1, motorlist=timer_motor_list)

        yield from bps.mv(pos_ophyd, pos)
        # yield from save_ophyd_value(pos_ophyd)

        # Setup XRF acquisition waiting
        st = Status()
        wait_active = False

        def wait_for_xmap(old_value, value, **kwargs):
            if wait_active:
                if value == "Done":
                    print("XRF acquisition done")
                    st.set_finished()
                    xrf.acquiring.unsubscribe_all()

        xrf.acquiring.subscribe(wait_for_xmap)
        wait_active = True

        # Trigger detectors
        yield from xrf.set_erase_start(1)
        yield from sis3820.software_trig(1)

        # Wait for XRF acquisition to complete
        yield from run_blocking_function(st.wait)

        timer.end_iteration()


def _step1d_xrfnc(devices, fileplugins, pos_ophyd, pos_arr, timer, timer_motor_list, y_index=None):
    """
    Core detector execution function used by both step1d and step2d plans.
    Handles detector synchronization and data capture during the scan.

    Parameters
    ----------
    devices : list
        List of ophyd devices
    fileplugins : list
        List of file plugins
    pos_ophyd : ophyd.Device
        Positioner device (samx, samy, or samz)
    pos_arr : numpy.ndarray
        Array of positions to scan
    timer : loop_timer_context
        Timer context for tracking scan progress
    timer_motor_list : list
        List of ophyd motor devices to track in the timer
    y_index : int, optional
        Y index for 2D scans (used for timer iteration calculation)

    Yields
    ------
    Various bluesky plan operations
    """

    status = DetectorFileSignal(fileplugins, devices, subscribe_fileplugins=False)

    for fileplugin in fileplugins:
        if fileplugin is not None:
            yield from fileplugin.set_capture("CAPTURING")

    for det in devices:
        if det.name == "xrf":
            xrf = det
        elif det.name == "sis3820":
            sis3820 = det

    # for det in devices:
    #     if det.name == "sis3820":
    #         yield from det.set_erase_start(1)
    #     elif det.name == "xrf":
    #         yield from det.set_erase_start(1)

    num_pts = len(pos_arr)
    for j, pos in enumerate(pos_arr):
        # Handle timer iteration for both 1D and 2D scans
        if y_index is not None:
            # 2D scan context
            timer.iteration(y_index * num_pts + j + 1, motorlist=timer_motor_list)
        else:
            # 1D scan context
            timer.iteration(j + 1, motorlist=timer_motor_list)

        # status.scan_active = True
        yield from bps.mv(pos_ophyd, pos)
        # yield from save_ophyd_value(pos_ophyd)

        # Setup XRF acquisition waiting
        st = Status()
        wait_active = False

        def wait_for_xmap(old_value, value, **kwargs):
            if wait_active:
                if value == "Done":
                    print("XRF acquisition done")
                    st.set_finished()
                    xrf.acquiring.unsubscribe_all()

        xrf.acquiring.subscribe(wait_for_xmap)
        wait_active = True

        # Trigger detectors
        yield from xrf.set_erase_start(1)
        yield from sis3820.software_trig(1)

        # Wait for XRF acquisition to complete
        yield from run_blocking_function(st.wait)

        timer.end_iteration()


def _common_stepscan_cleanup(devices_dict):
    """
    Common cleanup function that handles scan completion tasks for both step1d and step2d plans.

    Parameters
    ----------
    devices_dict : dict
        Dictionary of ophyd devices with device names as keys

    Yields
    ------
    Various bluesky plan operations for cleanup
    """
    logger.info("Scan completed")
    yield from bps.sleep(0.2)

    for det_name, det in devices_dict.items():
        if det_name == "sis3820":
            yield from det.set_external_trigger()
        elif det_name == "xrf":
            yield from det.after_stepscan()

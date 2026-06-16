"""
Common functionality for stepscan plans (step1d and step2d).

This module provides shared functions and utilities that are used by both step1d and step2d
stepscan plans, eliminating code duplication and providing a centralized location for
common operations.

Functions:
----------
_common_stepscan_setup(sis3820_on, xp3_on, tmm1_on, preamp1_on, preamp2_on, total_pts, dwell_ms, filename)
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
from mic_common.utils.validation import validate_scan_parameters, validate_device_connections
import logging
from ..utils.nexus_bps_func import save_ophyd_value
from ..utils.fly import DetectorFileSignal
import numpy as np
from ..utils.step import setup_detectors_and_fileio
from ..plans.toggle_usercalc import enable_usercalc, disable_usercalc
import time
iconfig = get_config()
logger = logging.getLogger(__name__)

def _common_stepscan_setup(
    devices=None,
    stepsize_x=0, 
    stepsize_y=0, 
    x_center=None,
    y_center=None,
    width=0, 
    height=0, 
    dwell_s=0, 
    ):
    
    """
    Common setup function that handles detector configuration and file I/O setup.
    Parameters
    ----------
    devices : list
        List of ophyd devices
    stepsize_x : float
        Step size in x direction
    stepsize_y : float
        Step size in y direction
    x_center : float
        Center position in x direction
    y_center : float
        Center position in y direction
    width : float
        Width of the scan
    height : float
        Height of the scan
    dwell_s : float
        Dwell time in seconds

    Returns
    -------
    tuple
        (devices_dict, fileplugins_dict) - devices and fileplugins as dicts with device names as keys
    """

    """Check input parameters and detector status"""
    logger.info("Validating scan parameters and detector status")
    validate_scan_parameters(stepsize_x=stepsize_x, stepsize_y=stepsize_y, width=width, height=height)

    """Construct the scan points and calculate the motor speeds"""
    logger.info("Constructing the scan points and calculating the motor speeds")
    xarr = np.arange(x_center - width / 2, x_center + width / 2, stepsize_x)
    npts_x = len(xarr)
    x_start = xarr[0]
    x_end = xarr[-1]
    if height is not None:
        yarr = np.arange(y_center - height / 2, y_center + height / 2, stepsize_y)
        npts_y = len(yarr)
        y_start = yarr[0]
        y_end = yarr[-1]
    else:
        y_start = None
        y_end = None
        npts_y = 0

    logger.info(f"x_start: {x_start}, x_end: {x_end}, npts_x: {npts_x}")
    logger.info(f"y_start: {y_start}, y_end: {y_end}, npts_y: {npts_y}")
        
    """Setup detectors and file I/O"""
    logger.info("Setting up detectors and file I/O")
    for det in devices:
        det.config_stepscan(
            num_pulses=npts_x,
            dwell_time=dwell_s,
            stepsize=stepsize_x,
        )
        det.stage()
    yield from bps.checkpoint()

    return 
    
def _step2d_scanrecord(
    width=0,
    x_center=None,
    stepsize_x=0,
    height=0,
    y_center=None,
    stepsize_y=0,
    dwell_sec=0,
    scaler_on=True,
    xp3_on=True,
    xmap_on=False,
    **kwargs,
):

    """Load ophyd objects"""
    scanrecord = oregistry["scanrecord"]
    sample = oregistry["sample"]
    savedata = oregistry["savedata"]
    step_dwell = oregistry["step_dwell"]

    """Disable the usercalc that used in scan record"""
    yield from disable_usercalc()

    """Check input parameters and detector status"""
    logger.info("Validating scan parameters and detector status")
    validate_scan_parameters(stepsize_x=stepsize_x, stepsize_y=stepsize_y, width=width, height=height)

    """Set up inner / outer scan record based on the scan types and parameters"""
    det_bools = [scaler_on, xp3_on, xmap_on]
    det_names = ["scaler", "xp3", "xmap"]
    devices = validate_device_connections(det_bools, det_names, return_devices=True)
    yield from bps.checkpoint()

    """Move the sample to the requested x and y position"""
    sample.x.set_speed() #sets to maximum
    x_center = x_center if x_center is not None else (round(sample.x.position - width / 2, 2))
    y_center = y_center if y_center is not None else (round(sample.y.position - height / 2, 2))
    yield from bps.mv(sample.x, x_center)
    yield from bps.mv(sample.y, y_center)

    yield from scanrecord.step.stage2Dstep(devices, sample, width, stepsize_x, height, stepsize_y, dwell_sec)
    yield from bps.checkpoint()
    logger.info("Scanrecord setup complete")

    """Assign the per-pixel dwell time"""
    logger.info(f"Setting per-pixel dwell time ({step_dwell.pvname}) to {dwell_sec} seconds")
    yield from bps.mv(step_dwell, dwell_sec)
    yield from bps.checkpoint()

    """Update the next file name"""
    savedata.update_next_file_name()
    fname = savedata.next_file_name

    """Now lets configure and stage the detectors"""
    for det in devices:
        if det.name == "xp3":
            xrf = det
            xrf.config_stepscan(num_pulses=scanrecord.step.inner.number_points.get(), 
                                dwell_time=dwell_sec)
            xrf.stage()
        elif det.name == "scaler":
            scaler = det
            scaler.config_stepscan(dwell_time=dwell_sec)
            scaler.stage()
    
    """Start executing scan"""
    yield from scanrecord.step.execute2Dstep(scan_name=fname)

    """Enable the usercalc that used in scan record"""
    yield from enable_usercalc()

    time.sleep(0.5)
    yield from scanrecord.step.unstage2Dstep()
    for d in devices:
        if d.name == "xp3":
            d.unstage()
        elif d.name == "scaler":
            d.unstage()

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

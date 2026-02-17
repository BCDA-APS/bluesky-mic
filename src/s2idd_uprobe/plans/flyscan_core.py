"""
Common functionality for flyscan plans (fly1d and fly2d).

This module provides shared functions and utilities that are used by both fly1d and fly2d
flyscan plans, eliminating code duplication and providing a centralized location for
common operations.

@author: yluo(grace227)
"""

import bluesky.plan_stubs as bps
from apsbits.core.instrument_init import oregistry
from apstools.plans import run_blocking_function
# from s2idd_uprobe.plans.toggle_usercalc import enable_usercalc, disable_usercalc
from mic_common.utils.validation import validate_scan_parameters, validate_device_connections
from s2idd_uprobe.utils.fly import (
    reorder_devices,
    setup_detectors_and_fileio,
    setup_motor_positions_and_speeds,
    calculate_x_scan_parameters,
    DetectorFileSignal,
)
from s2idd_uprobe.utils.nexus_bps_func import save_ophyd_value
from mic_common.utils.timer_decorator import loop_timer_context
import logging
import numpy as np

logger = logging.getLogger(__name__)


def _common_flyscan_setup(
    det_bools=None,
    det_names=None,
    x_center=None,
    y_center=None,
    width=0,
    height=None,
    stepsize_x=0,
    stepsize_y=None,
    dwell_ms=0,
):
    """
    Common setup for both fly1d and fly2d plans.

    Parameters
    ----------
    det_bools : list
        List of boolean values for each detector
    det_names : list
        List of detector names
    x_center : float, optional
        Center of scan in x direction
    y_center : float, optional
        Center of scan in y direction
    width : float
        Width of scan
    height : float
        Height of scan
    stepsize_x : float
        Step size in x direction
    stepsize_y : float, optional
        Step size in y direction (for 2D scans)
    dwell : float
        Dwell time

    Returns
    -------
    tuple
        (devices, xarr, x_start, x_end, x_motor_scan_speed, x_motor_retrace, num_pulses)
    """


    """Check input parameters and detector status"""
    logger.info("Validating scan parameters and detector status")
    validate_scan_parameters(
        stepsize_x=stepsize_x, stepsize_y=stepsize_y, width=width, height=height
    )
    devices = validate_device_connections(
        det_bools=det_bools, det_names=det_names, return_devices=True
    )

    """Construct the scan points and calculate the motor speeds"""
    logger.info("Constructing the scan points and calculating the motor speeds")
    xarr, x_start, x_end, x_motor_scan_speed, x_motor_retrace, num_pulses = (
        calculate_x_scan_parameters(width, x_center, stepsize_x, dwell_ms)
    )
    logger.info(
        f"x_start: {x_start}, x_end: {x_end}, x_motor_scan_speed: {x_motor_scan_speed}, num_pulses: {num_pulses}"
    )

    yarr = None
    if height is not None:
        yarr = np.arange(y_center - height / 2, y_center + height / 2, stepsize_y)
        logger.info(
            f"y_start: {yarr[0]}, y_end: {yarr[-1]}, num_pulses: {len(yarr)}"
        )

    """Setup detectors and file I/O"""
    logger.info("Setting up detectors and file I/O")
    numpts_x = len(xarr)
    num_pulses = numpts_x - 2
    setup_detectors_and_fileio(devices, num_pulses=num_pulses, dwell_time=dwell_ms, stepsize=stepsize_x)
    yield from bps.checkpoint()


    """Setup motor positions and speeds"""
    yield from setup_motor_positions_and_speeds(x_start)

    """Lets move the sis3820 device to the end of the list of devices"""
    devices = reorder_devices(devices)

    # return devices, xarr, x_start, x_end, x_motor_scan_speed, x_motor_retrace
    return devices, x_start, x_end, yarr
    

def _fly2d_scanrecord(
    width=0,
    x_center=None,
    stepsize_x=0,
    height=0,
    y_center=None,
    stepsize_y=0,
    dwell_ms=0,
    sample_z=None,
    xrf_on=True,
    preamp1_on=False,
    **kwargs,
):
    """Load ophyd objects"""
    scanrecord = oregistry["scanrecord"]
    fscanh_dwell = oregistry["fscanh_dwell"]
    fscanh_samx = oregistry["fscanh_samx"]
    sample = oregistry["sample"]
    savedata = oregistry["savedata"]
    flycalc = oregistry['fly_calc10']
    
    """Disable the usercalc that used in scan record"""
    # yield from disable_usercalc()
    if flycalc.value == 0:
        yield from bps.mv(flycalc, 1)

    """Move the sample to the requested z position"""
    if sample_z is not None:
        yield from bps.mv(sample.z, sample_z)
    if x_center is not None:
        yield from bps.mv(sample.x, x_center)
    if y_center is not None:
        yield from bps.mv(sample.y, y_center)

    """Set up inner / outer scan record based on the scan types and parameters"""
    det_bools = [True, xrf_on, preamp1_on]
    det_names = ["sis3820", "xrf", "tmm1"]
    devices = validate_device_connections(det_bools, det_names, return_devices=True)
    yield from scanrecord.fly.stage2Dfly(
        devices, sample, fscanh_samx, width, stepsize_x, height, stepsize_y
    )
    logger.info("after validataion")
    yield from bps.checkpoint()

    """Assign the per-pixel dwell time"""
    logger.info(f"Setting per-pixel dwell time ({fscanh_dwell.pvname}) to {dwell_ms} ms")
    yield from bps.mv(fscanh_dwell, dwell_ms)
    yield from bps.checkpoint()

    # TODO: """Generate scan_master.h5 file"""

    """Initialize detectors with desired pts, exposure time and file writer """
    numpts_x = scanrecord.fly.inner.number_points.value
    num_pulses = numpts_x - 2
    x_motor_scan_speed = sample.x.calculate_scan_speed(stepsize_x, dwell_ms)
    sample.x.scan_speed = x_motor_scan_speed

    setup_detectors_and_fileio(devices, num_pulses=num_pulses, dwell_time=dwell_ms, stepsize=stepsize_x)
    yield from bps.checkpoint()

    """Start executing scan"""
    fname = savedata.next_file_name
    # yield from scanrecord.fly.execute2Dfly(scan_name=fname, sample=sample)
    yield from scanrecord.fly.execute2Dfly(scan_name=fname)

    """Enable the usercalc that used in scan record"""
    yield from bps.mv(flycalc, 0)
    sample.x.set_speed(sample.x.get_max_velocity())
    yield from bps.checkpoint()
    # yield from enable_usercalc()

    yield from scanrecord.fly.unstage2Dfly()
    for d in devices:
        d.unstage()


def _fly2d(
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
    **kwargs,
):
    
    """Load ophyd objects"""
    sample = oregistry['sample']
    savedata = oregistry['savedata']


    """Disable usercalc"""
    # yield from disable_usercalc()
    # yield from bps.mv(retrace_samx_passive, 0)

    """Check input parameters and detector status"""
    logger.info("Validating scan parameters and detector status")
    validate_scan_parameters(
        stepsize_x=stepsize_x, stepsize_y=stepsize_y, width=width, height=height
    )
    x_center = x_center if x_center is not None else (round(sample.x.position - width / 2, 2))
    y_center = y_center if y_center is not None else (round(sample.y.position - height / 2, 2))
    sample_z = sample_z if sample_z is not None else (round(sample.z.position, 2))
    yield from bps.mv(sample.x, x_center)
    yield from bps.mv(sample.y, y_center)
    yield from bps.mv(sample.z, sample_z)

    det_bools = [True, xrf_on, preamp1_on]
    det_names = ["sis3820", "xrf", "tmm1"]
    devices, x_start, x_end, yarr = yield from _common_flyscan_setup(
        det_bools=det_bools, det_names=det_names, x_center=x_center, y_center=y_center,
        width=width, height=height, stepsize_x=stepsize_x, stepsize_y=stepsize_y, 
        dwell_ms=dwell_ms
    )


    """Main loop for the fly2d scan"""
    x_target = [x_end, x_start]
    filename = savedata.next_file_name

    with loop_timer_context(f"Data saved to {filename}", total_iterations=len(yarr)) as timer:
        for i, y in enumerate(yarr):
            timer.iteration(i + 1, samy=y)
            yield from bps.mv(sample.y, y)
            yield from save_ophyd_value(sample.y)

            if i == 0:
                print("Open shutter")
                savedata.advance_scan_number()

            if snake_scan:
                x_target_pos = x_target[i % 2]
                yield from _fly1d_core(devices, sample.x, x_target_pos)
            else:
                x_target_pos = x_end
                yield from _fly1d_core(devices, sample.x, x_target_pos)
                sample.x.set_speed()
                yield from bps.mv(sample.x, x_start)
                sample.x.set_speed(sample.x.scan_speed)
                logger.debug(f"x_motor velocity = {sample.x.velocity.get()}")
            timer.end_iteration()
            yield from bps.checkpoint()

    """Common cleanup for flyscan plans"""
    sample.x.set_speed()
    # yield from enable_usercalc()
    # yield from bps.mv(retrace_samx_passive, 2)



def _fly1d(
    width: float = 0,
    x_center: float = None,
    stepsize_x: float = 0,
    dwell_ms: float = 0,
    sample_z: float = None,
    xrf_on: bool = True,
    preamp1_on: bool = False,
    **kwargs,
):
    
    """Load ophyd object"""
    sample = oregistry['sample']
    savedata = oregistry['savedata']

    """Check input parameters"""
    logger.info("Validating scan parameters")
    validate_scan_parameters(stepsize_x=stepsize_x, width=width, dwell_ms=dwell_ms)
    x_center = x_center if x_center is not None else (round(sample.x.position - width / 2, 2))
    sample_z = sample_z if sample_z is not None else (round(sample.z.position, 2))
    yield from bps.mv(sample.x, x_center)
    yield from bps.mv(sample.z, sample_z)

    det_bools = [True, xrf_on, preamp1_on]
    det_names = ["sis3820", "xrf", "tmm1"]
    devices, x_start, x_end, _ = yield from _common_flyscan_setup(
        det_bools=det_bools, det_names=det_names, x_center=x_center, 
        width=width, stepsize_x=stepsize_x,
        dwell_ms=dwell_ms
    )

    """Disable usercalc"""
    # yield from disable_usercalc()
    # yield from bps.mv(retrace_samx_passive, 0)


    # TODO: open shutter
    print("open shutter")
    
    """Execute the fly1d scan"""
    filename = savedata.next_file_name
    savedata.advance_scan_number()
    with loop_timer_context(f"Data saved to {filename}", total_iterations=1) as timer:
        timer.iteration(1, samx=sample.x)
        yield from _fly1d_core(devices, sample.x, x_end)
        timer.end_iteration()
    yield from bps.checkpoint()
    
    """Restore motor speed and scan cleanup"""
    sample.x.set_speed()
    yield from bps.mv(sample.x, x_start)
    # yield from enable_usercalc()
    # yield from bps.mv(retrace_samx_passive, 2)
    logger.info(f"Scan is finished, filename: {filename}")



def _fly1d_core(devices, samx, x_end):
    """
    This function is being used in both fly1d and fly2d plans.

    Parameters
    ----------
    devices : list
        List of ophyd devices
    samx : ophyd.Device
        Sample x motor
    x_end : float
        End position for x motor
    """
    status = DetectorFileSignal(devices)

    for det in devices:
        fileplugin = getattr(det, 'fileplugin', None)
        if fileplugin is not None:
            fileplugin.capture.put(1)
        
        cam = getattr(det, 'cam', None)
        if cam is None:
            cam = det
        if ("sis3820" in cam.name) or ("xrf" in cam.name):
            cam.erase_start.put(1)
        elif "tmm" in cam.name:
            cam.acquire.put(1)
        
        yield from bps.sleep(0.2)

    # yield from bps.sleep(0.2)
    status.scan_active = True
    logger.debug(f"scan_active: {status.scan_active}")
    yield from save_ophyd_value(samx)
    yield from bps.mv(samx, x_end)
    yield from save_ophyd_value(samx)
    yield from bps.sleep(0.2)
    yield from run_blocking_function(status.st.wait)
    status.unsubscribe()

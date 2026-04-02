"""
Common functionality for flyscan plans (fly1d and fly2d).

This module provides shared functions and utilities that are used by both fly1d and fly2d
flyscan plans, eliminating code duplication and providing a centralized location for
common operations.

@author: yluo(grace227)
"""

import bluesky.plan_stubs as bps
from apsbits.core.instrument_init import oregistry
from mic_common.utils.validation import validate_scan_parameters, validate_device_connections
from bnp.utils.fly import setup_detectors_and_fileio
import logging

logger = logging.getLogger(__name__)
scanrecord = oregistry["scanrecord"]
sample = oregistry["sample"]
fly_dwell = oregistry["fly_dwell"]
savedata = oregistry["savedata"]
bda = oregistry["bda"]


def _move_with_timeout(device, target, *, timeout=10, retries=3, retry_delay=0.5, atol=0.001):
    if target is None:
        return

    current = getattr(device, "position", None)
    if current is not None and abs(current - target) <= atol:
        logger.info(f"Skipping move for {device.name}; already at target {target}")
        return

    attempts = retries + 1
    last_exc = None
    for attempt in range(1, attempts + 1):
        group = f"{device.name}_move_{attempt}"
        try:
            logger.info(
                f"Moving {device.name} to {target} (attempt {attempt}/{attempts}, timeout={timeout}s)"
            )
            yield from bps.abs_set(device, target, wait=False, group=group)
            yield from bps.wait(group=group, timeout=timeout)

            current = getattr(device, "position", None)
            if current is None or abs(current - target) <= atol:
                return
            logger.warning(f"{device.name} move completed but readback {current} is not at target {target}")
        except Exception as exc:
            last_exc = exc
            stop_signal = getattr(device, "stop_signal", None)
            if stop_signal is not None:
                try:
                    stop_signal.put(1)
                except Exception as stop_exc:
                    logger.warning(f"Failed to stop {device.name} after move timeout/error: {stop_exc}")

            yield from bps.sleep(retry_delay)
            current = getattr(device, "position", None)
            if current is not None and abs(current - target) <= atol:
                logger.info(f"{device.name} reached target {target} after retry delay")
                return

            if attempt >= attempts:
                logger.exception(
                    f"Move failed for {device.name} -> {target} after {attempts} attempts; last readback={current}"
                )
                raise last_exc

            logger.warning(
                f"Move failed or timed out for {device.name} -> {target}; current={current}; retrying ({attempt}/{attempts})"
            )

    if last_exc is not None:
        raise last_exc


def piezo_centering():
    logger.info(f"Centering piezo motors")
    yield from bps.mv(sample.y.piezo.center, 1)
    yield from bps.mv(sample.x.piezo.center, 1)
    yield from bps.sleep(5)


def _fly2d_scanrecord(
    width=0,
    x_center=None,
    stepsize_x=0,
    height=0,
    y_center=None,
    stepsize_y=0,
    dwell_ms=0,
    sample_z=None,
    theta=None,
    bda_position=None,
    xmap_on=True,
    xp3_on=False,
    eiger_on=False,
    ptycho_exp_factor=1,
    **kwargs,
):
    """Validate scan parameters"""
    validate_scan_parameters(stepsize_x=stepsize_x, stepsize_y=stepsize_y, width=width, height=height)

    """To move sample motors we need to be in combine motion"""
    sample.x.motion.put(1)  # 1: CombinedStep; 4: FlyScan; 3: FineScan
    sample.y.motion.put(1)  # 1: CombinedStep; 4: FlyScan; 3: FineScan
    sample_z = sample_z if sample_z is not None else (round(sample.z.position, 2))
    sample_x = x_center if x_center is not None else (round(sample.x.piezo.position, 2))
    sample_y = y_center if y_center is not None else (round(sample.y.piezo.position, 2))
    yield from _move_with_timeout(sample.theta, theta, timeout=10, retries=4, atol=0.02)
    yield from bps.mv(sample.z, sample_z)
    yield from bps.mv(sample.x.piezo, sample_x)
    yield from bps.mv(sample.y.piezo, sample_y)
    yield from bps.mv(bda.x, bda_position)
    yield from piezo_centering()
    yield from bps.checkpoint()

    """Set up inner / outer scan record based on the scan types and parameters"""
    det_bools = [xmap_on, xp3_on, eiger_on]
    det_names = ["xmap", "xp3", "eiger"]
    devices = validate_device_connections(det_bools, det_names, return_devices=True)
    yield from scanrecord.stage2Dfly(
        devices, sample, width, stepsize_x, height, stepsize_y
    )
    yield from bps.checkpoint()

    """Assign the per-pixel dwell time"""
    logger.info(f"Setting per-pixel dwell time ({fly_dwell.pvname}) to {dwell_ms} ms")
    yield from bps.mv(fly_dwell, dwell_ms)
    yield from bps.checkpoint()

    """Initialize detectors with desired pts, exposure time and file writer """
    numpts_x = scanrecord.inner.number_points.value
    num_pulses = numpts_x
    setup_detectors_and_fileio(devices, num_pulses=num_pulses, dwell_time=dwell_ms, stepsize=stepsize_x)
    yield from bps.checkpoint()

    """Start executing scan"""
    yield from piezo_centering()
    yield from piezo_centering()
    
    logger.info(f"Opening BDA")
    yield from _move_with_timeout(bda.x, bda_position, timeout=10, retries=4, atol=0.02)
    sample.x.motion.put(3)
    logger.info(f"Putting sample x motor to fly scan mode")
    fname = savedata.next_file_name
    yield from scanrecord.execute2Dfly(scan_name=fname)

    yield from scanrecord.unstage2Dfly()

    logger.info(f"Closing BDA")
    bda_block = bda_position + 1500 # 1500 um
    yield from _move_with_timeout(bda.x, bda_block, timeout=10, retries=4, atol=0.02)
    sample.x.motion.put(1)
    logger.info(f"Putting sample x motor to combined mode")
    yield from bps.mv(sample.y.piezo.center, 1)
    logger.info(f"Centering Y-piezo motors after scan")

    ## unstage detectors
    for det in devices:
        det.unstage()
    yield from scanrecord.unstage2Dfly()


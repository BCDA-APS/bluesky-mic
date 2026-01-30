"""
Common functionality for flyscan plans (fly1d and fly2d).

This module provides shared functions and utilities that are used by both fly1d and fly2d
flyscan plans, eliminating code duplication and providing a centralized location for
common operations.

@author: yluo(grace227)
"""

import bluesky.plan_stubs as bps
from apsbits.core.instrument_init import oregistry
# from s2idd_uprobe.plans.toggle_usercalc import enable_usercalc, disable_usercalc
from mic_common.utils.validation import validate_scan_parameters, validate_device_connections
import logging

logger = logging.getLogger(__name__)
scanrecord = oregistry["scanrecord"]
sample = oregistry["sample"]
fly_dwell = oregistry["fly_dwell"]
savedata = oregistry["savedata"]


def _fly2d_scanrecord(
    width=0,
    x_center=None,
    stepsize_x=0,
    height=0,
    y_center=None,
    stepsize_y=0,
    dwell_ms=0,
    sample_z=None,
    xmap_on=True,
    xp3_on=True,
    eiger_on=True,
    ptycho_exp_factor=1,
    **kwargs,
):
    """Validate scan parameters"""
    validate_scan_parameters(stepsize_x=stepsize_x, stepsize_y=stepsize_y, width=width, height=height)

    """To move sample motors we need to be in combine motion"""
    sample.x.motion.put(1)  # 1: CombinedStep; 4: FlyScan
    sample.y.motion.put(1)  # 1: CombinedStep; 4: FlyScan
    sample_z = sample_z if sample_z is not None else (round(sample.z.position, 2))
    sample_x = x_center if x_center is not None else (round(sample.x.piezo.position, 2))
    sample_y = y_center if y_center is not None else (round(sample.y.piezo.position, 2))
    yield from bps.mv(sample.z, sample_z)
    yield from bps.mv(sample.x.piezo, sample_x)
    yield from bps.mv(sample.y.piezo, sample_y)
    yield from bps.checkpoint()

    """Set up inner / outer scan record based on the scan types and parameters"""
    det_bools = [True, xmap_on, xp3_on, eiger_on]
    det_names = ["sis3820", "xmap", "xp3", "eiger"]
    devices = validate_device_connections(det_bools, det_names, return_devices=True)
    yield from scanrecord.stage2Dfly(
        devices, sample, width, stepsize_x, height, stepsize_y
    )
    yield from bps.checkpoint()

    """Assign the per-pixel dwell time"""
    logger.info(f"Setting per-pixel dwell time ({fly_dwell.pvname}) to {dwell_ms} ms")
    yield from bps.mv(fly_dwell, dwell_ms)
    yield from bps.checkpoint()

    """Start executing scan"""
    yield from bps.mv(sample.y.piezo.center, 1)
    yield from bps.mv(sample.x.piezo.center, 1)
    logger.info(f"Centering piezo motors before scan")
    #TODO: open BDA
    logger.info(f"Opening BDA")
    sample.x.motion.put(4)
    logger.info(f"Putting sample x motor to fly scan mode")
    fname = savedata.next_file_name
    yield from scanrecord.execute2Dfly(scan_name=fname)

    """Enable the usercalc that used in scan record"""
    # yield from enable_usercalc()

    yield from scanrecord.unstage2Dfly()
    #TODO: close BDA
    logger.info(f"Closing BDA")
    sample.x.motion.put(1)
    logger.info(f"Putting sample x motor to combined mode")
    yield from bps.mv(sample.y.piezo.center, 1)
    logger.info(f"Centering Y-piezo motors after scan")


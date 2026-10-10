"""Simple step-scan XANES plan for BNP."""

import logging

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import oregistry

from mic_common.utils.param_capture import capture_params
from bnp.plans.flyscan_core import piezo_centering

logger = logging.getLogger(__name__)

xanes_scanrecord = oregistry["xanes_scanrecord"]
xmap = oregistry["xmap"]
savedata = oregistry["savedata"]
savedata_xanes = oregistry["savedata_xanes"]
sample = oregistry["sample"]
bda = oregistry["bda"]
kohzu_mono = oregistry["kohzu_mono"]

def sync_xanes_savedata():
    """Synchronize the file path of the SaveData object with the EPICS AreaDetector filewriter."""
    det_path = xmap.fileplugin.generate_det_filepath()
    sync_path = xmap.fileplugin.sync_file_path(det_path)
    mda_path = sync_path.split("/../", 1)[0] + "/"

    yield from bps.mv(savedata_xanes.file_system, mda_path)
    yield from bps.mv(
        savedata_xanes.next_scan_number,
        savedata.next_scan_number.get(),
    )
    savedata_xanes.update_next_file_name()


def _xanes_1d(
    x_center,
    y_center,
    sample_z,
    energy_width_keV,
    energy_step_keV,
    dwell_s,
    bda_position,
    **kwargs
):
    """Execute one scan using the preconfigured 9idbXMAP:scan1 record."""
    try:
        if kohzu_mono.mode.get() == 0: # 1 is auto, 0 is manual
            logger.warning("Kohzu monochromator is in manual mode. Switching to auto mode for XANES scan.")
            yield from bps.mv(kohzu_mono.mode, 1)
            yield from bps.sleep(1)

        sample.x.motion.put(1)  # 1: CombinedStep; 4: FlyScan; 3: FineScan
        sample.y.motion.put(1)  # 1: CombinedStep; 4: FlyScan; 3: FineScan

        sample_z = sample_z if sample_z is not None else (round(sample.z.position, 2))
        sample_x = x_center if x_center is not None else (round(sample.x.piezo.position, 2))
        sample_y = y_center if y_center is not None else (round(sample.y.piezo.position, 2))

        yield from bps.mv(sample.z, sample_z)
        yield from bps.mv(sample.x.piezo, sample_x)
        yield from bps.mv(sample.y.piezo, sample_y)
        yield from piezo_centering()
        yield from bps.checkpoint()

        yield from xanes_scanrecord.stage_xanes(energy_width_keV, energy_step_keV, kohzu_mono.setpoint.pvname)
        xmap.config_stepscan(dwell_time=dwell_s * 1000)  #dwell_time is in ms for XMAP
        xmap.stage()
        yield from bps.mv(bda.x, bda_position)
        yield from bps.sleep(1)

        yield from xanes_scanrecord.execute1Dstep(scan_name=savedata_xanes.next_file_name)
        
    finally:
        # Match flyscan_core: block the BDA after every scan, including errors.
        try:
            xmap.unstage()
        except Exception as e:
            logger.warning(f"Error unstaging XMAP after XANES scan: {e}")

        try:
            xanes_scanrecord.unstage_xanes()
        except Exception as e:
            logger.warning(f"Error unstaging XANES scanrecord after XANES scan: {e}")

        try:
            savedata.next_scan_number.put(savedata_xanes.next_scan_number.get())
        except Exception as e:
            logger.warning(f"Error syncing savedata scan number after XANES scan: {e}")

        yield from bps.mv(bda.x, bda_position + 1500)
        yield from bps.sleep(1)


def xanes_1d(
    samplename: str = "smp1",
    user_comments: str = "",
    x_center: float = None,
    y_center: float = None,
    sample_z: float = None,
    energy_width_keV: float = 0,
    energy_step_keV: float = 0,
    dwell_s: float = 0,
    bda_position: float = None,
):
    """Run one archived-style BNP XANES step scan.

    The monochromator drive PV, scan triggers, and detector setup are expected
    to be configured in ``9idbXMAP:scan1`` by the IOC. This plan changes only
    the sample position, ``P1WD``, ``P1SI``, ``PresetReal``, and ``EXSC``.

    Parameters
    ----------
    x_center, y_center:
        Sample x/y positions in the same units as the sample piezo devices.
    sample_z:
        Sample z position.
    energy_width_keV:
        Total scan width in keV; this is ``9idbXMAP:scan1.P1WD``.
    energy_step_keV:
        Energy step in keV; this is ``9idbXMAP:scan1.P1SI``.
    dwell_s:
        XMAP real-time preset in seconds; this is ``9idbXMAP:PresetReal``.
    """
    x_center = sample.x.piezo.position if x_center is None else x_center
    y_center = sample.y.piezo.position if y_center is None else y_center
    sample_z = sample.z.position if sample_z is None else sample_z
    bda_position = bda.x.position if bda_position is None else bda_position

    if energy_width_keV <= 0:
        raise ValueError("energy_width_keV must be greater than zero")
    if energy_step_keV <= 0:
        raise ValueError("energy_step_keV must be greater than zero")
    if dwell_s <= 0:
        raise ValueError("dwell_s must be greater than zero")

    plan_args = capture_params(xanes_1d, **locals())
    scan_id = None
    try:
        yield from sync_xanes_savedata()
        scan_id = savedata_xanes.next_scan_number.get()
    except Exception as e:
        logger.error(f"Error getting scan id: {e}")
        scan_id = None

    md = {"plan_args": plan_args, "scan_id": scan_id}

    @bpp.run_decorator(md=md)
    def _plan():
        yield from _xanes_1d(**plan_args)

    yield from _plan()

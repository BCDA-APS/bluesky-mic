"""QServer helper functions exposed from the BNP startup session."""

from __future__ import annotations

import logging
import time
from typing import Optional

from apsbits.core.instrument_init import oregistry
from bnp.utils.coordinate_transform import coordinate_transform
from .beamline_monitor import BNPMonitorPolicy
from .recovery_state import set_detector_recovering
from .beamline_monitor import get_named_monitor_snapshot as _get_named_monitor_snapshot
from .beamline_monitor import get_plan_monitor_snapshot as _get_plan_monitor_snapshot

logger = logging.getLogger(__name__)
_Y_PIEZO_RECOVERY_DEVICES = ["sample", "scanrecord", "fly_dwell", "ring", "xmap", "xp3", "eiger"]


def _get_savedata():
    return oregistry.find("savedata", allow_none=True)


def _get_sample():
    return oregistry.find("sample", allow_none=True)


def _get_sample_coor_offset():
    return oregistry.find("sample_coor_offset", allow_none=True)


def _get_transform_offsets() -> dict[str, float]:
    offsets = _get_sample_coor_offset()
    if offsets is None:
        raise RuntimeError("sample_coor_offset device is not available")
    return {
        "xo": float(offsets.x_sample_origin.get()),
        "yo": float(offsets.y_sample_origin.get()),
        "zo": float(offsets.z_sample_origin.get()),
        "xa": float(offsets.x_optical_axis.get()),
        "ya": float(offsets.y_optical_axis.get()),
        "za": float(offsets.z_optical_axis.get()),
    }


def get_save_data_path() -> Optional[str]:
    """Return the current save-data path visible to the GUI."""

    savedata = _get_savedata()
    if savedata is None:
        logger.warning("savedata device is not available")
        return None
    try:
        path = savedata.get_auto_storage_path()
        logger.info(f"Save-data path: {path}")
        return path
    except Exception:
        logger.exception("Failed to read save-data path")
        return None


def syncXYZ() -> list[float] | None:
    """Return the current sample X/Y/Z positions as ``[x, y, z]``."""

    sample = _get_sample()
    if sample is None:
        logger.warning("sample device is not available")
        return None
    try:
        return [
            round(float(sample.x.piezo.position), 2),
            round(float(sample.y.piezo.position), 2),
            round(float(sample.z.position), 2),
        ]
    except Exception:
        logger.exception("Failed to read sample XYZ positions")
        return None


def syncXYZ_transform(
    x: float | None = None,
    y: float | None = None,
    z: float | None = None,
    theta: float | None = None,
    tolerance: float = 0.02,
) -> dict[str, float] | None:
    """Transform theta-0 sample coordinates into scan coordinates at ``theta``."""

    sample = _get_sample()
    if sample is None:
        logger.warning("sample device is not available")
        return None

    try:
        x_value = round(float(sample.x.piezo.position), 2) if x is None else float(x)
        y_value = round(float(sample.y.piezo.position), 2) if y is None else float(y)
        z_value = round(float(sample.z.position), 2) if z is None else float(z)
        current_theta = round(float(sample.theta.position), 2)
        target_theta = current_theta if theta is None else float(theta)
        if abs(round(current_theta, 2)) > tolerance:
            logger.warning("Theta is not 0, cannot transform sample XYZ coordinates")
            return None
        return coordinate_transform(target_theta, x_value, y_value, z_value, **_get_transform_offsets())
    except Exception:
        logger.exception("Failed to transform sample XYZ coordinates")
        return None


def get_global_health_snapshot(manifest_path: str | None = None) -> dict[str, object]:
    """Return an enriched baseline monitor snapshot using worker-side device access."""

    try:
        return _get_named_monitor_snapshot(
            ["sample", "scanrecord", "fly_dwell", "ring"],
            manifest_path=manifest_path,
        )
    except Exception as exc:
        logger.exception("Failed to build global health snapshot")
        return {
            "timestamp": None,
            "device_names": [],
            "devices": {},
            "pv_backend": "qserver-worker",
            "manifest_path": manifest_path,
            "error": str(exc),
        }


def get_named_monitor_snapshot(
    device_names: list[str],
    manifest_path: str | None = None,
) -> dict[str, object]:
    """Return an enriched monitor snapshot for an explicit device list."""

    try:
        return _get_named_monitor_snapshot(
            list(device_names),
            manifest_path=manifest_path,
        )
    except Exception as exc:
        logger.exception("Failed to build named monitor snapshot")
        return {
            "timestamp": None,
            "device_names": list(device_names),
            "devices": {},
            "pv_backend": "qserver-worker",
            "manifest_path": manifest_path,
            "error": str(exc),
        }


def get_plan_monitor_snapshot(
    plan_name: str,
    plan_args: dict[str, object] | None = None,
    include_baseline: bool = True,
    manifest_path: str | None = None,
) -> dict[str, object]:
    """Return an enriched plan-aware monitor snapshot using worker-side device access."""

    try:
        return _get_plan_monitor_snapshot(
            plan_name,
            plan_args=plan_args,
            include_baseline=include_baseline,
            manifest_path=manifest_path,
        )
    except Exception as exc:
        logger.exception("Failed to build plan monitor snapshot")
        return {
            "timestamp": None,
            "plan_name": plan_name,
            "plan_args": dict(plan_args or {}),
            "device_names": [],
            "devices": {},
            "pv_backend": "qserver-worker",
            "manifest_path": manifest_path,
            "error": str(exc),
        }


def recover_detector(
    device_name: str,
    retries: int = 1,
) -> dict[str, object]:
    """Invoke detector-specific unhang logic in the worker environment."""

    device = oregistry.find(device_name, allow_none=True)
    if device is None:
        return {
            "device": device_name,
            "success": False,
            "error": f"{device_name} not found in oregistry",
        }
    if not hasattr(device, "unhang"):
        return {
            "device": device_name,
            "success": False,
            "error": f"{device_name} does not implement unhang()",
        }

    set_detector_recovering(device_name, True)
    try:
        result = device.unhang(retries=retries)
        if isinstance(result, dict):
            result.setdefault("device", device_name)
            return result
        return {
            "device": device_name,
            "success": True,
            "result": result,
        }
    except Exception as exc:
        logger.exception("Failed to recover detector %s", device_name)
        return {
            "device": device_name,
            "success": False,
            "error": str(exc),
        }
    finally:
        set_detector_recovering(device_name, False)


def recover_y_piezo(
    *,
    inner_scan_timeout: float = 30.0,
    poll_period_s: float = 0.2,
) -> dict[str, object]:
    """Center the sample y piezo after the inner scan is idle and detectors look healthy."""

    sample = oregistry.find("sample", allow_none=True)
    if sample is None:
        return {
            "device": "sample.y.piezo",
            "success": False,
            "error": "sample device is not available",
        }

    policy = BNPMonitorPolicy()
    deadline = time.monotonic() + max(0.0, float(inner_scan_timeout))

    try:
        while time.monotonic() <= deadline:
            snapshot = _get_named_monitor_snapshot(_Y_PIEZO_RECOVERY_DEVICES)
            detector_name = _hung_detector_during_y_recovery(policy, snapshot)
            if detector_name is not None:
                logger.warning("Aborting y piezo recovery because detector %s appears hung", detector_name)
                return {
                    "device": "sample.y.piezo",
                    "success": False,
                    "error": f"Detector {detector_name} appears hung during y piezo recovery",
                }
            if _inner_scan_finished(snapshot):
                break
            time.sleep(max(0.05, float(poll_period_s)))
        else:
            return {
                "device": "sample.y.piezo",
                "success": False,
                "error": "Timed out waiting for inner scan to finish",
            }

        sample.y.piezo.center.put(1)
        logger.warning("Manually centered sample.y.piezo")
        return {
            "device": "sample.y.piezo",
            "success": True,
        }
    except Exception as exc:
        logger.exception("Failed to manually recover sample.y.piezo")
        return {
            "device": "sample.y.piezo",
            "success": False,
            "error": str(exc),
        }


def _inner_scan_finished(snapshot: dict[str, object]) -> bool:
    devices = snapshot.get("devices")
    if not isinstance(devices, dict):
        return False
    scanrecord = devices.get("scanrecord")
    if not isinstance(scanrecord, dict):
        return False
    pvs = scanrecord.get("pvs")
    if not isinstance(pvs, dict):
        return False
    inner_execute = pvs.get("inner.execute_scan")
    if not isinstance(inner_execute, dict):
        return False
    value = inner_execute.get("value")
    if value is None:
        value = inner_execute.get("char_value")
    try:
        return float(value) == 0.0
    except Exception:
        return str(value).strip().lower() in {"0", "idle", "done", "false", "off"}


def _hung_detector_during_y_recovery(
    policy: BNPMonitorPolicy,
    snapshot: dict[str, object],
) -> str | None:
    devices = snapshot.get("devices")
    if not isinstance(devices, dict):
        return None
    for detector_name in ("xmap", "xp3", "eiger"):
        device = devices.get(detector_name)
        if not isinstance(device, dict):
            continue
        if policy._detector_hung(
            detector_name,
            snapshot,
            ignore_scan_pause=True,
            ignore_outer_wait=True,
        ):
            return detector_name
    return None

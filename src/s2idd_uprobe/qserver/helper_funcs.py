"""QServer helper functions exposed from the S2IDD startup session."""

from __future__ import annotations

import logging

from apsbits.core.instrument_init import oregistry

from .beamline_monitor import get_named_monitor_snapshot as _get_named_monitor_snapshot
from .beamline_monitor import get_plan_monitor_snapshot as _get_plan_monitor_snapshot
from .recovery_state import set_detector_recovering

logger = logging.getLogger(__name__)


def get_save_data_path():
    savedata = oregistry.find("savedata", allow_none=True)
    if savedata is None:
        return None
    return savedata.get_auto_storage_path()


def get_current_mda_file():
    savedata = oregistry.find("savedata", allow_none=True)
    if savedata is None:
        return None
    return savedata.next_file_name


def create_dm_experiment(
    experiment_name: str,
    root_path: str,
    esaf_id: int | str | None = None,
) -> dict[str, object]:
    """Create/register a DM experiment from the QServer worker."""
    try:
        from mic_common.dm.agent import get_dm_agent

        create_kwargs = {
            "experiment_name": experiment_name,
            "root_path": root_path,
        }
        if esaf_id is not None and str(esaf_id).strip():
            create_kwargs["esaf_id"] = esaf_id
        experiment = get_dm_agent().create_experiment(
            **create_kwargs,
        )
        logger.info("DM experiment details: %s", experiment)
    except Exception as exc:
        logger.exception("Failed to create DM experiment %s", experiment_name)
        return {"success": False, "error": str(exc)}
    return {"success": True, "experiment": experiment}


def start_dm_daq(
    experiment_name: str,
    data_directory: str,
    process_existing: bool = True,
    max_run_time_hours: float | int | None = 1000,
) -> dict[str, object]:
    """Start DM real-time directory monitoring/upload from the QServer worker."""
    daq_info = {}
    if process_existing:
        daq_info["processExistingFiles"] = True
    if max_run_time_hours is not None:
        daq_info["maxRunTimeInHours"] = int(max_run_time_hours)

    try:
        from mic_common.dm.agent import get_dm_agent

        daq = get_dm_agent().start_daq(
            experiment_name,
            data_directory,
            **daq_info,
        )
        logger.info("DM DAQ details: %s", daq)
    except Exception as exc:
        logger.exception("Failed to start DM DAQ for %s", experiment_name)
        return {"success": False, "error": str(exc)}
    return {"success": True, "daq": daq}


def get_global_health_snapshot(manifest_path: str | None = None) -> dict[str, object]:
    try:
        return _get_named_monitor_snapshot(
            [
                "ring",
                "sample",
                "scanrecord_fly",
                "scanrecord_step",
                "kohzu_mono",
                "zp_z",
                "xrf",
                "sis3820",
                "fscanh_dwell",
            ],
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

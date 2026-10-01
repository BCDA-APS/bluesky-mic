"""QServer-facing helpers for APS Data Management operations."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def create_dm_experiment(
    experiment_name: str,
    root_path: str,
    esaf_id: int | str | None = None,
) -> dict[str, object]:
    """Create/register a DM experiment and return a QServer-safe response."""

    try:
        from .agent import get_dm_agent

        create_kwargs: dict[str, object] = {
            "experiment_name": experiment_name,
            "root_path": root_path,
        }
        if esaf_id is not None and str(esaf_id).strip():
            create_kwargs["esaf_id"] = esaf_id

        experiment = get_dm_agent().create_experiment(**create_kwargs)
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
    """Start DM real-time directory monitoring and return a QServer-safe response."""

    daq_info: dict[str, object] = {}
    if process_existing:
        daq_info["processExistingFiles"] = True
    if max_run_time_hours is not None:
        daq_info["maxRunTimeInHours"] = int(max_run_time_hours)

    try:
        from .agent import get_dm_agent

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


__all__ = ["create_dm_experiment", "start_dm_daq"]

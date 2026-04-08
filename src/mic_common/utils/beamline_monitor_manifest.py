"""Generate a plan-aware beamline monitor manifest from an ophyd registry."""

from __future__ import annotations

import json, yaml
from pathlib import Path
from typing import Any, Mapping
import logging

logger = logging.getLogger(__name__)


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(v) for v in value]
    return str(value)


def _safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
    try:
        return getattr(obj, attr)
    except Exception:
        return default


def _signal_record(signal: Any) -> dict[str, Any]:
    record = {
        "pvname": _safe_getattr(signal, "pvname"),
        "read_pv": _safe_getattr(signal, "read_pv"),
        "write_pv": _safe_getattr(signal, "write_pv"),
        "kind": _json_value(_safe_getattr(signal, "kind")),
    }
    return {key: value for key, value in record.items() if value not in (None, "")}


def _self_signal_record(obj: Any) -> dict[str, dict[str, Any]]:
    pvname = _safe_getattr(obj, "pvname")
    read_pv = _safe_getattr(obj, "read_pv")
    write_pv = _safe_getattr(obj, "write_pv")
    if not (pvname or read_pv or write_pv):
        return {}
    return {"value": _signal_record(obj)}


def _resolve_attr_path(obj: Any, dotted_path: str) -> Any:
    target = obj
    if dotted_path in {"", "value"}:
        return target
    for part in dotted_path.split("."):
        target = getattr(target, part)
    return target


def _collect_selected_records(device: Any, include_paths: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if not include_paths:
        records.update(_self_signal_record(device))
        return records

    for path in include_paths:
        if not isinstance(path, str) or not path:
            continue
        if path == "value":
            records.update(_self_signal_record(device))
            continue
        try:
            component = _resolve_attr_path(device, path)
        except Exception:
            logger.debug("Unable to resolve beamline monitor path '%s'", path, exc_info=True)
            continue

        pvname = _safe_getattr(component, "pvname")
        read_pv = _safe_getattr(component, "read_pv")
        write_pv = _safe_getattr(component, "write_pv")
        if pvname or read_pv or write_pv:
            records[path] = _signal_record(component)
    return records


def _load_manifest_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, Mapping):
        raise ValueError(f"Beamline monitor config must be a mapping: {path}")
    return dict(payload)


def generate_beamline_monitor_manifest(
    *,
    oregistry: Any,
    output_path: str | Path,
    config_path: str | Path | None = None,
    plan_profiles: Mapping[str, Any] | None = None,
    device_rules: Mapping[str, Any] | None = None,
) -> Path:
    """Write a JSON monitor manifest for use by client-side monitor tools."""

    if config_path is not None:
        config = _load_manifest_config(config_path)
        if plan_profiles is None:
            plan_profiles = config.get("plans")
        if device_rules is None:
            device_rules = config.get("devices")

    plan_profiles = dict(plan_profiles or {})
    device_rules = dict(device_rules or {})

    manifest: dict[str, Any] = {
        "version": 1,
        "plans": _json_value(plan_profiles),
        "devices": {},
    }

    for device_name, rule in device_rules.items():
        device = oregistry.find(device_name, allow_none=True)
        if device is None:
            manifest["devices"][device_name] = {
                "category": rule.get("category", "device"),
                "missing": True,
                "signals": {},
                "extras": _json_value(rule.get("extra_pvs", {})),
            }
            continue

        include_paths = tuple(rule.get("include", ()))
        selected = _collect_selected_records(device, include_paths)
        extra_pvs = {
            key: {"pvname": pvname}
            for key, pvname in dict(rule.get("extra_pvs", {})).items()
        }

        manifest["devices"][device_name] = {
            "category": rule.get("category", "device"),
            "registry_name": device_name,
            "signal_count": len(selected) + len(extra_pvs),
            "signals": _json_value(selected),
            "extras": _json_value(extra_pvs),
        }
        logger.info("Device %s added to beamline monitor list", device_name)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return output


__all__ = ["generate_beamline_monitor_manifest"]

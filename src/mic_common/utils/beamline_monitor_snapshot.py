"""Shared worker-side snapshot collection for beamline monitors."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from apsbits.core.instrument_init import oregistry
from ophyd import EpicsSignalRO

from .beamline_monitor_policy import BeamlineMonitorPolicy


_EXTRA_SIGNAL_CACHE: dict[str, Any] = {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {str(k): to_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_json_value(v) for v in value]
    return str(value)


def load_manifest(manifest_path: str | None, default_manifest_path: str | Path) -> tuple[dict[str, Any], str]:
    path = Path(manifest_path) if manifest_path else Path(default_manifest_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid beamline monitor manifest: {path}")
    return data, str(path)


def is_enabled(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"", "0", "false", "no", "off", "none"}:
            return False
        if normalized in {"1", "true", "yes", "on"}:
            return True
        return False
    return bool(value)


def resolve_device_names(
    plan_name: str,
    plan_args: Mapping[str, Any] | None,
    *,
    plans: Mapping[str, Any],
    include_baseline: bool = True,
) -> list[str]:
    profile = plans.get(plan_name, {})
    if not isinstance(profile, Mapping):
        profile = {}
    names: list[str] = []
    if include_baseline:
        baseline = profile.get("baseline", ())
        if isinstance(baseline, (list, tuple)):
            names.extend(str(name) for name in baseline)
    conditional = profile.get("conditional_detectors", {})
    if isinstance(conditional, Mapping):
        for arg_name, device_name in conditional.items():
            if is_enabled((plan_args or {}).get(arg_name)):
                names.append(str(device_name))
    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        if name not in seen:
            seen.add(name)
            deduped.append(name)
    return deduped


def resolve_attr(obj: Any, dotted_path: str) -> Any:
    target = obj
    if dotted_path in {"", "value"}:
        return target
    for part in dotted_path.split("."):
        target = getattr(target, part)
    return target


def format_timestamp(raw: Any) -> str | None:
    if raw in (None, ""):
        return None
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            raw = raw.replace(tzinfo=timezone.utc)
        return raw.isoformat()
    try:
        return datetime.fromtimestamp(float(raw), tz=timezone.utc).isoformat()
    except Exception:
        return str(raw)


def signal_snapshot(signal: Any, *, pvname_hint: str | None = None) -> dict[str, Any]:
    pvname = pvname_hint or getattr(signal, "pvname", None) or getattr(signal, "read_pv", None)
    connected = True
    if hasattr(signal, "connected"):
        try:
            connected = bool(signal.connected)
        except Exception:
            connected = False
    if not connected:
        return {
            "pvname": str(pvname) if pvname not in (None, "") else None,
            "connected": False,
            "value": None,
            "char_value": None,
            "severity": to_json_value(getattr(signal, "severity", None)),
            "status": to_json_value(getattr(signal, "status", None)),
            "timestamp": format_timestamp(getattr(signal, "timestamp", None)),
            "error": "Signal is not connected",
        }

    try:
        value = signal.get()
    except Exception as exc:
        return {
            "pvname": str(pvname) if pvname not in (None, "") else None,
            "connected": False,
            "value": None,
            "char_value": None,
            "severity": to_json_value(getattr(signal, "severity", None)),
            "status": to_json_value(getattr(signal, "status", None)),
            "timestamp": format_timestamp(getattr(signal, "timestamp", None)),
            "error": str(exc),
        }
    try:
        char_value = signal.get(as_string=True)
    except Exception:
        char_value = None
    return {
        "pvname": str(pvname) if pvname not in (None, "") else None,
        "connected": True,
        "value": to_json_value(value),
        "char_value": None if char_value in (None, "") else str(char_value),
        "severity": to_json_value(getattr(signal, "severity", None)),
        "status": to_json_value(getattr(signal, "status", None)),
        "timestamp": format_timestamp(getattr(signal, "timestamp", None)),
        "error": None,
    }


def snapshot_device(device_name: str, device_spec: Mapping[str, Any]) -> dict[str, Any]:
    category = str(device_spec.get("category", "unknown"))
    device = oregistry.find(device_name, allow_none=True)
    if device is None:
        return {
            "name": device_name,
            "category": category,
            "pv_count": 0,
            "pvs": {},
            "error": f"{device_name} not found in oregistry",
        }

    signals = device_spec.get("signals", {})
    pvs: dict[str, Any] = {}
    if isinstance(signals, Mapping):
        for key, signal_spec in signals.items():
            if not isinstance(signal_spec, Mapping):
                continue
            try:
                signal = resolve_attr(device, str(key))
                pvs[str(key)] = signal_snapshot(signal, pvname_hint=signal_spec.get("pvname"))
            except Exception as exc:
                pvs[str(key)] = {
                    "pvname": signal_spec.get("pvname"),
                    "connected": False,
                    "value": None,
                    "char_value": None,
                    "severity": None,
                    "status": None,
                    "timestamp": None,
                    "error": str(exc),
                }

    extras = device_spec.get("extras", {})
    if isinstance(extras, Mapping):
        for key, pvname in extras.items():
            try:
                signal = resolve_attr(device, str(key))
            except Exception:
                signal = _EXTRA_SIGNAL_CACHE.get(str(pvname))
                if signal is None:
                    signal = EpicsSignalRO(str(pvname), name=str(key), auto_monitor=False)
                    _EXTRA_SIGNAL_CACHE[str(pvname)] = signal
            pvs[str(key)] = signal_snapshot(signal, pvname_hint=str(pvname))

    return {
        "name": device_name,
        "category": category,
        "pv_count": len(pvs),
        "pvs": pvs,
    }


def enrich_snapshot(snapshot: Mapping[str, Any], *, policy: BeamlineMonitorPolicy) -> dict[str, Any]:
    enriched = dict(snapshot)
    devices = snapshot.get("devices")
    devices = dict(devices) if isinstance(devices, Mapping) else {}
    enriched_devices: dict[str, Any] = {}
    for device_name, device in devices.items():
        if not isinstance(device, Mapping):
            continue
        enriched_devices[device_name] = policy.enrich_device(device_name, device, snapshot)
    enriched["devices"] = enriched_devices
    enriched["activity"] = policy.summarize_activity(enriched)
    return enriched


def get_named_monitor_snapshot(
    device_names: list[str],
    *,
    manifest_path: str | None,
    default_manifest_path: str | Path,
    policy: BeamlineMonitorPolicy,
) -> dict[str, Any]:
    manifest, loaded_manifest_path = load_manifest(manifest_path, default_manifest_path)
    devices = manifest.get("devices", {})
    if not isinstance(devices, Mapping):
        devices = {}

    names = [str(name) for name in device_names if str(name) in devices]
    snapshot = {
        "timestamp": utc_now(),
        "device_names": names,
        "devices": {name: snapshot_device(name, devices[name]) for name in names},
        "pv_backend": "qserver-worker",
        "manifest_path": loaded_manifest_path,
        "error": None,
    }
    return enrich_snapshot(snapshot, policy=policy)


def get_plan_monitor_snapshot(
    plan_name: str,
    plan_args: Mapping[str, Any] | None = None,
    *,
    include_baseline: bool = True,
    manifest_path: str | None,
    default_manifest_path: str | Path,
    policy: BeamlineMonitorPolicy,
) -> dict[str, Any]:
    manifest, loaded_manifest_path = load_manifest(manifest_path, default_manifest_path)
    devices = manifest.get("devices", {})
    plans = manifest.get("plans", {})
    if not isinstance(devices, Mapping):
        devices = {}
    if not isinstance(plans, Mapping):
        plans = {}

    device_names = resolve_device_names(
        plan_name,
        plan_args,
        plans=plans,
        include_baseline=include_baseline,
    )
    snapshot = {
        "timestamp": utc_now(),
        "plan_name": str(plan_name),
        "plan_args": to_json_value(dict(plan_args or {})),
        "device_names": device_names,
        "devices": {name: snapshot_device(name, devices[name]) for name in device_names if name in devices},
        "pv_backend": "qserver-worker",
        "manifest_path": loaded_manifest_path,
        "error": None,
    }
    return enrich_snapshot(snapshot, policy=policy)


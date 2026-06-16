"""Shared helper functions for beamline monitor policies."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping


def parse_timestamp(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


def pv_value(pv: Any) -> Any:
    if isinstance(pv, Mapping):
        value = pv.get("char_value")
        if value not in (None, ""):
            return value
        return pv.get("value")
    return None


def truthy_pv(pv: Any) -> bool:
    value = pv_value(pv)
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized not in {"", "0", "false", "done", "idle", "off", "go"}
    return bool(value)


def pv_at_least_one(pv: Any) -> bool:
    value = pv_value(pv)
    try:
        return float(value) >= 1
    except Exception:
        return False


def pv_float(pv: Any) -> float | None:
    value = pv_value(pv)
    try:
        return float(value)
    except Exception:
        return None


def canonical_pv_key(key: str) -> str:
    return key.strip().lower().replace("_", ".").replace("-", ".")


def find_matching_pv(pvs: Mapping[str, Any], *aliases: str) -> Any:
    normalized_aliases = [canonical_pv_key(alias) for alias in aliases if isinstance(alias, str) and alias]
    if not normalized_aliases:
        return None
    for alias in aliases:
        if alias in pvs:
            return pvs.get(alias)
    for key, pv in pvs.items():
        normalized_key = canonical_pv_key(str(key))
        if normalized_key in normalized_aliases:
            return pv
    for alias in normalized_aliases:
        if "." not in alias:
            continue
        alias_parts = alias.split(".")
        for key, pv in pvs.items():
            normalized_key = canonical_pv_key(str(key))
            if normalized_key.split(".")[-len(alias_parts) :] == alias_parts:
                return pv
    return None


def pv_value_by_aliases(pvs: Mapping[str, Any], *aliases: str) -> Any:
    return pv_value(find_matching_pv(pvs, *aliases))


def has_any_pv(pvs: Mapping[str, Any], *aliases: str) -> bool:
    return find_matching_pv(pvs, *aliases) is not None


def device_category(device: Mapping[str, Any]) -> str:
    category = device.get("category")
    return category.strip().lower() if isinstance(category, str) else ""


def collect_axis_states(pvs: Mapping[str, Any]) -> list[tuple[str, Any, Any]]:
    axes: list[tuple[str, Any, Any]] = []
    axis_aliases = {
        "x": (("x.piezo.readback", "x.stepper.readback", "x.readback", "x.motion"), ("x.piezo.setpoint", "x.stepper.setpoint", "x.setpoint", "x.request")),
        "y": (("y.piezo.readback", "y.stepper.readback", "y.readback", "y.motion"), ("y.piezo.setpoint", "y.stepper.setpoint", "y.setpoint", "y.request")),
        "z": (("z.readback", "z.motion"), ("z.setpoint", "z.request")),
        "theta": (("theta.readback", "theta.motion"), ("theta.setpoint", "theta.request")),
    }
    for axis, (readback_aliases, setpoint_aliases) in axis_aliases.items():
        readback = pv_value_by_aliases(pvs, *readback_aliases)
        setpoint = pv_value_by_aliases(pvs, *setpoint_aliases)
        if readback is None and setpoint is None:
            continue
        axes.append((axis, readback, setpoint))
    return axes


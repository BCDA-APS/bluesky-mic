"""Transient worker-side detector recovery state for BNP monitor policy."""

from __future__ import annotations

from threading import Lock


_RECOVERING_DETECTORS: set[str] = set()
_RECOVERY_LOCK = Lock()


def set_detector_recovering(device_name: str, recovering: bool) -> None:
    with _RECOVERY_LOCK:
        if recovering:
            _RECOVERING_DETECTORS.add(str(device_name))
        else:
            _RECOVERING_DETECTORS.discard(str(device_name))


def is_detector_recovering(device_name: str) -> bool:
    with _RECOVERY_LOCK:
        return str(device_name) in _RECOVERING_DETECTORS


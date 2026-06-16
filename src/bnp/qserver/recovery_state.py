"""Transient worker-side detector recovery state for BNP monitor policy."""

from __future__ import annotations

from threading import Lock


_RECOVERING_DETECTORS: set[str] = set()
_RECOVERY_LOCK = Lock()
_Y_PIEZO_RECOVERY_CONSUMED = False
_Y_PIEZO_RECOVERY_LOCK = Lock()


def set_detector_recovering(device_name: str, recovering: bool) -> None:
    with _RECOVERY_LOCK:
        if recovering:
            _RECOVERING_DETECTORS.add(str(device_name))
        else:
            _RECOVERING_DETECTORS.discard(str(device_name))


def is_detector_recovering(device_name: str) -> bool:
    with _RECOVERY_LOCK:
        return str(device_name) in _RECOVERING_DETECTORS


def consume_y_piezo_recovery_request(*, active: bool) -> bool:
    """Return True once per over-limit event when y-piezo recovery should be issued."""

    global _Y_PIEZO_RECOVERY_CONSUMED

    with _Y_PIEZO_RECOVERY_LOCK:
        if not active:
            _Y_PIEZO_RECOVERY_CONSUMED = False
            return False
        if _Y_PIEZO_RECOVERY_CONSUMED:
            return False
        _Y_PIEZO_RECOVERY_CONSUMED = True
        return True

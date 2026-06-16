"""BNP-specific beamline monitor policy and snapshot assembly."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping

from apsbits.core.instrument_init import oregistry

from .recovery_state import is_detector_recovering
from mic_common.utils.beamline_monitor_helpers import collect_axis_states
from mic_common.utils.beamline_monitor_helpers import device_category
from mic_common.utils.beamline_monitor_helpers import find_matching_pv
from mic_common.utils.beamline_monitor_helpers import has_any_pv
from mic_common.utils.beamline_monitor_helpers import parse_timestamp
from mic_common.utils.beamline_monitor_helpers import pv_at_least_one
from mic_common.utils.beamline_monitor_helpers import pv_float
from mic_common.utils.beamline_monitor_helpers import pv_value
from mic_common.utils.beamline_monitor_helpers import pv_value_by_aliases
from mic_common.utils.beamline_monitor_helpers import truthy_pv
from mic_common.utils.beamline_monitor_policy import BeamlineMonitorPolicy
from mic_common.utils.beamline_monitor_snapshot import get_named_monitor_snapshot as _get_named_snapshot
from mic_common.utils.beamline_monitor_snapshot import get_plan_monitor_snapshot as _get_plan_snapshot


_DEFAULT_MANIFEST_PATH = Path(__file__).with_name("beamline_monitor.json")
_DETECTOR_TIMEOUT_FACTOR = 3.0
_SAMPLE_POSITION_TOLERANCE = 0.1

logger = logging.getLogger(__name__)

class BNPMonitorPolicy(BeamlineMonitorPolicy):
    def _infer_device_role(self, device_name: str, device: Mapping[str, Any]) -> str:
        category = device_category(device)
        if category in {"scanrecord", "detector", "motion", "signal"}:
            return category
        if category in {"storebeam", "ring"}:
            return "ring"
        pvs = device.get("pvs")
        if not isinstance(pvs, Mapping):
            return "device"
        if has_any_pv(pvs, "outer.current_point", "outer.number_points", "outer.scan_phase", "pause_signal", "scan_pause"):
            return "scanrecord"
        if has_any_pv(pvs, "cam.acquire", "fileplugin.capture", "capture", "acquire", "fileplugin.file_name", "file_name"):
            return "detector"
        if has_any_pv(pvs, "current", "operating_mode") and "ring" in device_name.lower():
            return "ring"
        if collect_axis_states(pvs) or has_any_pv(pvs, "busy", "done"):
            return "motion"
        return "device"

    def _scanrecord_device(self, snapshot: Mapping[str, Any]) -> Mapping[str, Any] | None:
        devices = snapshot.get("devices")
        if not isinstance(devices, Mapping):
            return None
        for name, device in devices.items():
            if isinstance(device, Mapping) and self._infer_device_role(str(name), device) == "scanrecord":
                return device
        return None

    def _scanrecord_paused(
        self,
        pvs: Mapping[str, Any],
        *,
        ignore_scan_pause: bool = False,
        ignore_inner_wait: bool = False,
        ignore_outer_wait: bool = False,
    ) -> bool:
        paused = False
        if not ignore_scan_pause:
            paused = paused or truthy_pv(find_matching_pv(pvs, "scan_pause", "pause_signal"))
        if not ignore_inner_wait:
            paused = paused or pv_at_least_one(find_matching_pv(pvs, "inner_client_wait", "inner.wait"))
        if not ignore_outer_wait:
            paused = paused or pv_at_least_one(find_matching_pv(pvs, "outer_client_wait", "outer.wait"))
        return paused

    def _sample_hung_axes(self, snapshot: Mapping[str, Any], sample_name: str) -> list[str]:
        devices = snapshot.get("devices")
        if not isinstance(devices, Mapping):
            return []
        sample = devices.get(sample_name)
        if not isinstance(sample, Mapping):
            return []
        pvs = sample.get("pvs")
        if not isinstance(pvs, Mapping) or truthy_pv(find_matching_pv(pvs, "busy")):
            return []
        axes: list[str] = []
        axis_checks = {
            "x": [("x.piezo.setpoint", "x.piezo.readback"), ("x.stepper.setpoint", "x.stepper.readback"), ("x.setpoint", "x.readback")],
            "y": [("y.piezo.setpoint", "y.piezo.readback"), ("y.stepper.setpoint", "y.stepper.readback"), ("y.setpoint", "y.readback")],
            "z": [("z.setpoint", "z.readback")],
            "theta": [("theta.setpoint", "theta.readback")],
        }
        for axis, pairs in axis_checks.items():
            for setpoint_key, readback_key in pairs:
                setpoint = pv_float(find_matching_pv(pvs, setpoint_key))
                readback = pv_float(find_matching_pv(pvs, readback_key))
                if setpoint is None or readback is None:
                    continue
                if abs(setpoint - readback) > _SAMPLE_POSITION_TOLERANCE:
                    axes.append(axis)
                    break
        return axes

    def _ring_current(self, snapshot: Mapping[str, Any]) -> float | None:
        devices = snapshot.get("devices")
        if not isinstance(devices, Mapping):
            return None
        for name, device in devices.items():
            if not isinstance(device, Mapping) or self._infer_device_role(str(name), device) != "ring":
                continue
            pvs = device.get("pvs")
            if not isinstance(pvs, Mapping):
                continue
            try:
                return float(pv_value_by_aliases(pvs, "current"))
            except Exception:
                return None
        return None

    def _ring_mode(self, snapshot: Mapping[str, Any]) -> str:
        devices = snapshot.get("devices")
        if not isinstance(devices, Mapping):
            return ""
        for name, device in devices.items():
            if not isinstance(device, Mapping) or self._infer_device_role(str(name), device) != "ring":
                continue
            pvs = device.get("pvs")
            if not isinstance(pvs, Mapping):
                continue
            return str(pv_value_by_aliases(pvs, "operating_mode") or "")
        return ""

    def _fly_dwell_seconds(self, snapshot: Mapping[str, Any]) -> float | None:
        devices = snapshot.get("devices")
        if not isinstance(devices, Mapping):
            return None
        for name, device in devices.items():
            if not isinstance(device, Mapping):
                continue
            if str(name) != "fly_dwell" and self._infer_device_role(str(name), device) != "signal":
                continue
            pvs = device.get("pvs")
            if not isinstance(pvs, Mapping):
                continue
            try:
                dwell_ms = float(pv_value_by_aliases(pvs, "value"))
                return max(0.0, dwell_ms / 1000.0)
            except Exception:
                continue
        return None

    def _scanrecord_pvs(self, snapshot: Mapping[str, Any]) -> Mapping[str, Any] | None:
        scanrecord = self._scanrecord_device(snapshot)
        if not isinstance(scanrecord, Mapping):
            return None
        pvs = scanrecord.get("pvs")
        return pvs if isinstance(pvs, Mapping) else None

    def _scanrecord_float(self, snapshot: Mapping[str, Any], *aliases: str) -> float | None:
        pvs = self._scanrecord_pvs(snapshot)
        if not isinstance(pvs, Mapping):
            return None
        try:
            return float(pv_value_by_aliases(pvs, *aliases))
        except Exception:
            return None

    def _sample_pvs(self, snapshot: Mapping[str, Any]) -> Mapping[str, Any] | None:
        devices = snapshot.get("devices")
        if not isinstance(devices, Mapping):
            return None
        sample = devices.get("sample")
        if not isinstance(sample, Mapping):
            return None
        pvs = sample.get("pvs")
        return pvs if isinstance(pvs, Mapping) else None

    def _sample_float(self, snapshot: Mapping[str, Any], *aliases: str) -> float | None:
        pvs = self._sample_pvs(snapshot)
        if not isinstance(pvs, Mapping):
            return None
        try:
            return float(pv_value_by_aliases(pvs, *aliases))
        except Exception:
            return None

    def _sample_y_piezo_over_limit(self, snapshot: Mapping[str, Any]) -> tuple[bool, float | None, float | None]:
        sample = oregistry.find("sample", allow_none=True)
        if sample is None:
            return False, None, None

        piezo_value = self._sample_float(snapshot, "y.piezo_value")
        try:
            piezo_max_value = float(sample.y.piezo_max_value)
        except Exception:
            piezo_max_value = None
        if piezo_value is None or piezo_max_value is None:
            return False, piezo_value, piezo_max_value
        return piezo_value > piezo_max_value, piezo_value, piezo_max_value

    def _scan_phase_waiting_for_detectors(self, snapshot: Mapping[str, Any]) -> bool:
        scanrecord = self._scanrecord_device(snapshot)
        if not isinstance(scanrecord, Mapping):
            return False
        pvs = scanrecord.get("pvs")
        if not isinstance(pvs, Mapping):
            return False
        waiting_phases = {"WAIT:DETCTRS", "WAIT:AFTER_SCAN"}
        for key in ("inner.scan_phase", "outer.scan_phase", "inner_phase", "outer_phase"):
            phase = pv_value(find_matching_pv(pvs, key))
            if isinstance(phase, str) and phase.strip() in waiting_phases:
                return True
        return False

    def _detector_hung(
        self,
        device_name: str,
        snapshot: Mapping[str, Any],
        *,
        ignore_scan_pause: bool = False,
        ignore_outer_wait: bool = False,
    ) -> bool:
        devices = snapshot.get("devices")
        if not isinstance(devices, Mapping):
            return False
        device = devices.get(device_name)
        if not isinstance(device, Mapping):
            return False
        pvs = device.get("pvs")
        if not isinstance(pvs, Mapping):
            return False
        scanrecord = self._scanrecord_device(snapshot)
        if not isinstance(scanrecord, Mapping):
            return False
        scanrecord_pvs = scanrecord.get("pvs")
        if not isinstance(scanrecord_pvs, Mapping):
            return False
        if self._scanrecord_paused(
            scanrecord_pvs,
            ignore_scan_pause=ignore_scan_pause,
            ignore_outer_wait=ignore_outer_wait,
        ) or not self._scan_phase_waiting_for_detectors(snapshot):
            return False
        ring_current = self._ring_current(snapshot)
        if ring_current is None or ring_current <= 0:
            return False
        if device_name == "xmap":
            acquiring = truthy_pv(find_matching_pv(pvs, "fileplugin.capture")) or truthy_pv(
                find_matching_pv(pvs, "fileplugin.write_file", "write_status")
            )
        else:
            acquiring = truthy_pv(find_matching_pv(pvs, "cam.acquire", "acquire")) or truthy_pv(
                find_matching_pv(pvs, "fileplugin.capture", "capture")
            )
        if not acquiring:
            return False
        dwell_seconds = self._fly_dwell_seconds(snapshot)
        inner_point_count = self._scanrecord_float(snapshot, "inner.number_points")
        if dwell_seconds is None or dwell_seconds <= 0 or inner_point_count is None or inner_point_count <= 0:
            return False
        capture = find_matching_pv(pvs, "fileplugin.capture", "capture")
        if not isinstance(capture, Mapping):
            return False
        now_ts = parse_timestamp(snapshot.get("timestamp"))
        capture_ts = parse_timestamp(capture.get("timestamp"))
        if now_ts is None or capture_ts is None:
            return False
        age = (now_ts - capture_ts).total_seconds()
        timeout_seconds = _DETECTOR_TIMEOUT_FACTOR * inner_point_count * dwell_seconds
        return age > timeout_seconds

    def enrich_device(self, device_name: str, device: Mapping[str, Any], snapshot: Mapping[str, Any]) -> dict[str, Any]:
        enriched = dict(device)
        role = self._infer_device_role(device_name, device)
        recovering = role == "detector" and is_detector_recovering(device_name)
        detector_hung = role == "detector" and self._detector_hung(device_name, snapshot)
        enriched["role"] = role
        enriched["state"] = "recovering" if recovering else "hung" if detector_hung else "normal"
        enriched["health"] = self._evaluate_device_health(device_name, device, snapshot, role, recovering=recovering)
        enriched["summary"] = self._summarize_device(device_name, device, snapshot, role, recovering=recovering)
        enriched["actions"] = self._device_actions(device_name, role, recovering=recovering)
        return enriched

    def _evaluate_device_health(
        self,
        device_name: str,
        device: Mapping[str, Any],
        snapshot: Mapping[str, Any],
        role: str,
        *,
        recovering: bool = False,
    ) -> str:
        pvs = device.get("pvs")
        if not isinstance(pvs, Mapping) or not pvs:
            return "warning"
        if recovering:
            return "warning"
        if role == "ring":
            current = self._ring_current(snapshot)
            mode = self._ring_mode(snapshot).upper()
            if current is not None and current < 10 and "NO BEAM" in mode:
                return "error"
            if current is not None and current < 100:
                return "warning"
        if device_name == "sample" and self._sample_y_piezo_over_limit(snapshot)[0]:
            return "warning"
        if role == "scanrecord" and self._scanrecord_paused(pvs):
            return "warning"
        if role == "motion" and self._sample_hung_axes(snapshot, device_name):
            return "error"
        if role == "detector":
            detector_hung = self._detector_hung(device_name, snapshot)
            if detector_hung:
                return "error"
        connected = 0
        disconnected = 0
        degraded = 0
        for pv in pvs.values():
            if not isinstance(pv, Mapping):
                degraded += 1
                continue
            if pv.get("error"):
                degraded += 1
            if pv.get("connected"):
                connected += 1
            else:
                disconnected += 1
        if connected and not disconnected and not degraded:
            return "ok"
        if connected:
            return "warning"
        return "error"

    def _summarize_device(
        self,
        device_name: str,
        device: Mapping[str, Any],
        snapshot: Mapping[str, Any],
        role: str,
        *,
        recovering: bool = False,
    ) -> str:
        pvs = device.get("pvs")
        if not isinstance(pvs, Mapping):
            return "No PV data"
        if recovering:
            return "Recovering detector"
        if role == "scanrecord":
            if self._scanrecord_paused(pvs):
                reasons = []
                if truthy_pv(find_matching_pv(pvs, "scan_pause", "pause_signal")):
                    reasons.append("pause PV")
                if pv_at_least_one(find_matching_pv(pvs, "inner_client_wait", "inner.wait")):
                    reasons.append("inner wait")
                if pv_at_least_one(find_matching_pv(pvs, "outer_client_wait", "outer.wait")):
                    reasons.append("outer wait")
                return f"Paused by {', '.join(reasons) if reasons else 'pause state'}"
            current = pv_value_by_aliases(pvs, "outer.current_point", "outer_cpt")
            total = pv_value_by_aliases(pvs, "outer.number_points", "outer_npts")
            phase = pv_value_by_aliases(pvs, "outer.scan_phase", "outer_phase", "inner.scan_phase", "inner_phase")
            if current is not None and total is not None:
                return f"Progress {current}/{total}" + (f" | phase {phase}" if phase not in (None, "") else "")
            return "Waiting for scan record progress"
        if role == "detector":
            detector_hung = self._detector_hung(device_name, snapshot)
            if detector_hung:
                return "Detector hangs"
            parts = []
            if truthy_pv(find_matching_pv(pvs, "fileplugin.capture", "capture")):
                parts.append("capturing")
            if truthy_pv(find_matching_pv(pvs, "cam.acquire", "acquire")):
                parts.append("acquiring")
            num_capture = pv_value_by_aliases(pvs, "fileplugin.num_capture", "num_capture")
            if num_capture not in (None, ""):
                parts.append(f"num_capture={num_capture}")
            file_name = pv_value_by_aliases(pvs, "fileplugin.file_name", "file_name")
            if file_name not in (None, ""):
                parts.append(f"file={file_name}")
            detector_state = pv_value_by_aliases(pvs, "detector_state", "cam.detector_state")
            if detector_state not in (None, ""):
                parts.append(f"state={detector_state}")
            write_status = pv_value_by_aliases(pvs, "fileplugin.write_file", "write_status")
            if write_status not in (None, ""):
                parts.append(f"write={write_status}")
            return " | ".join(parts) if parts else "Detector online"
        if role == "motion":
            parts = []
            for axis, readback, setpoint in collect_axis_states(pvs):
                if readback is not None:
                    parts.append(f"{axis}={readback}")
                elif setpoint is not None:
                    parts.append(f"{axis}_set={setpoint}")
            busy = pv_value(find_matching_pv(pvs, "busy"))
            if truthy_pv(find_matching_pv(pvs, "busy")):
                parts.append("busy")
            elif truthy_pv(find_matching_pv(pvs, "done")):
                parts.append("done")
            hung_axes = self._sample_hung_axes(snapshot, device_name)
            if hung_axes:
                parts.append(f"motor hangs: {', '.join(hung_axes)}")
            if device_name == "sample":
                over_limit, piezo_value, piezo_max_value = self._sample_y_piezo_over_limit(snapshot)
                if piezo_value is not None:
                    parts.append(f"y_piezo_value={piezo_value}")
                if piezo_max_value is not None:
                    parts.append(f"y_piezo_max={piezo_max_value}")
                if over_limit:
                    parts.append("y piezo over limit")
            if busy in (0, "0", False):
                parts.append("ready")
            return " | ".join(parts) if parts else "Motion state unavailable"
        if device_name == "fly_dwell" or role == "signal":
            value = pv_value_by_aliases(pvs, "value")
            return f"dwell={value}" if value is not None else "Signal unavailable"
        if role == "ring":
            current = pv_value_by_aliases(pvs, "current")
            mode = pv_value_by_aliases(pvs, "operating_mode")
            parts = [
                f"current={current}" if current is not None else None,
                f"mode={mode}" if mode not in (None, "") else None,
            ]
            return " | ".join(part for part in parts if part) or "Ring state unavailable"
        connected = sum(1 for pv in pvs.values() if isinstance(pv, Mapping) and pv.get("connected"))
        return f"{connected}/{len(pvs)} PVs connected"

    def _device_actions(self, device_name: str, role: str, *, recovering: bool = False) -> dict[str, Any]:
        recover_supported = False
        if role == "detector" and not recovering:
            target = oregistry.find(device_name, allow_none=True)
            recover_supported = bool(target is not None and hasattr(target, "unhang"))
        return {"recover": recover_supported, "recovering": recovering}

    def summarize_activity(self, snapshot: Mapping[str, Any]) -> str:
        error = snapshot.get("error")
        if isinstance(error, str) and error in {"No running queue item found", "Running item is not an executable plan"}:
            return "idle"
        if error:
            return str(error)
        plan_name = snapshot.get("plan_name")
        devices = snapshot.get("devices")
        devices = dict(devices) if isinstance(devices, Mapping) else {}
        recovering = [
            str(device_name)
            for device_name, device in devices.items()
            if isinstance(device, Mapping) and device.get("state") == "recovering"
        ]
        if recovering:
            return f"Recovering detector: {', '.join(recovering)}"
        scanrecord = self._scanrecord_device(snapshot)
        if isinstance(scanrecord, Mapping):
            pvs = scanrecord.get("pvs")
            if isinstance(pvs, Mapping):
                if self._scanrecord_paused(pvs):
                    return f"{plan_name or 'Scan'} paused"
                current = pv_value_by_aliases(pvs, "outer.current_point", "outer_cpt")
                total = pv_value_by_aliases(pvs, "outer.number_points", "outer_npts")
                phase = pv_value_by_aliases(pvs, "outer.scan_phase", "outer_phase", "inner.scan_phase", "inner_phase")
                if current is not None and total is not None:
                    return f"{plan_name or 'Scan'} line {current}/{total}" + (
                        f" | phase {phase}" if phase not in (None, "") else ""
                    )
        for device_name, device in devices.items():
            if not isinstance(device, Mapping) or self._infer_device_role(str(device_name), device) != "detector":
                continue
            pvs = device.get("pvs")
            if not isinstance(pvs, Mapping):
                continue
            if truthy_pv(find_matching_pv(pvs, "fileplugin.capture", "capture")):
                return f"{device_name} capturing"
            if truthy_pv(find_matching_pv(pvs, "cam.acquire", "acquire")):
                return f"{device_name} acquiring"
            write_status = pv_value_by_aliases(pvs, "fileplugin.write_file", "write_status")
            if write_status not in (None, "", 0, "0"):
                return f"{device_name} writing file"
        return f"{plan_name or 'No active plan'} idle"


def get_named_monitor_snapshot(
    device_names: list[str],
    *,
    manifest_path: str | None = None,
) -> dict[str, Any]:
    return _get_named_snapshot(
        device_names,
        manifest_path=manifest_path,
        default_manifest_path=_DEFAULT_MANIFEST_PATH,
        policy=BNPMonitorPolicy(),
    )


def get_plan_monitor_snapshot(
    plan_name: str,
    plan_args: Mapping[str, Any] | None = None,
    *,
    include_baseline: bool = True,
    manifest_path: str | None = None,
) -> dict[str, Any]:
    return _get_plan_snapshot(
        plan_name,
        plan_args=plan_args,
        include_baseline=include_baseline,
        manifest_path=manifest_path,
        default_manifest_path=_DEFAULT_MANIFEST_PATH,
        policy=BNPMonitorPolicy(),
    )

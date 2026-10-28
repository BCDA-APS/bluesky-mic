"""S2IDD-specific beamline monitor policy and snapshot assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from mic_common.utils.beamline_monitor_helpers import collect_axis_states
from mic_common.utils.beamline_monitor_helpers import device_category
from mic_common.utils.beamline_monitor_helpers import find_matching_pv
from mic_common.utils.beamline_monitor_helpers import has_any_pv
from mic_common.utils.beamline_monitor_helpers import parse_timestamp
from mic_common.utils.beamline_monitor_helpers import pv_at_least_one
from mic_common.utils.beamline_monitor_helpers import pv_value
from mic_common.utils.beamline_monitor_helpers import pv_value_by_aliases
from mic_common.utils.beamline_monitor_helpers import truthy_pv
from mic_common.utils.beamline_monitor_policy import BeamlineMonitorPolicy
from mic_common.utils.beamline_monitor_snapshot import get_named_monitor_snapshot as _get_named_snapshot
from mic_common.utils.beamline_monitor_snapshot import get_plan_monitor_snapshot as _get_plan_snapshot
from .recovery_state import is_detector_recovering


_DEFAULT_MANIFEST_PATH = Path(__file__).with_name("beamline_monitor.json")
_DETECTOR_STALE_SECONDS = 10.0
_DETECTOR_TIMEOUT_FACTOR = 3.0


class S2IDDMonitorPolicy(BeamlineMonitorPolicy):
    def _infer_device_role(self, device_name: str, device: Mapping[str, Any]) -> str:
        category = device_category(device)
        if category in {"scanrecord", "detector", "motion", "signal"}:
            return category
        if category in {"storebeam", "ring"}:
            return "ring"
        pvs = device.get("pvs")
        if not isinstance(pvs, Mapping):
            return "device"
        if has_any_pv(pvs, "scan_phase", "scan_busy", "execute_scan", "current_point"):
            return "scanrecord"
        if has_any_pv(pvs, "current", "operating_mode") and "ring" in device_name.lower():
            return "ring"
        if has_any_pv(pvs, "cam.acquire", "fileplugin.capture", "capture", "write_file"):
            return "detector"
        if collect_axis_states(pvs) or has_any_pv(pvs, "motor_is_moving", "user_readback", "user_setpoint"):
            return "motion"
        return "device"

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

    def _scanrecord_device(self, snapshot: Mapping[str, Any]) -> Mapping[str, Any] | None:
        devices = snapshot.get("devices")
        if not isinstance(devices, Mapping):
            return None
        for name, device in devices.items():
            if isinstance(device, Mapping) and self._infer_device_role(str(name), device) == "scanrecord":
                return device
        return None

    @staticmethod
    def _scanrecord_kind(device_name: str, device: Mapping[str, Any]) -> str:
        role = str(device.get("role") or "")
        if role == "scanrecord_fly" or "scanrecord_fly" in device_name:
            return "fly"
        if role == "scanrecord_step" or "scanrecord_step" in device_name:
            return "step"
        pvs = device.get("pvs")
        if isinstance(pvs, Mapping) and find_matching_pv(pvs, "outer.scan_phase", "pause_signal", "wait") is not None:
            return "fly"
        return "step"

    def _scan_status(self, snapshot: Mapping[str, Any]) -> str:
        scanrecord = self._scanrecord_device(snapshot)
        if not isinstance(scanrecord, Mapping):
            return "idle"
        pvs = scanrecord.get("pvs")
        if not isinstance(pvs, Mapping):
            return "idle"
        kind = self._scanrecord_kind(str(scanrecord.get("name") or ""), scanrecord)

        phases = []
        for key in (
            "inner.scan_phase",
            "outer.scan_phase",
            "pause_signal",
            "wait",
        ):
            phase = pv_value(find_matching_pv(pvs, key))
            if isinstance(phase, str) and phase.strip():
                phases.append(phase.strip().lower())

        if any("pause" in phase for phase in phases):
            return "pause"
        if any("run" in phase or "scan" in phase for phase in phases):
            return "running"

        for key in ("inner.execute_scan", "outer.execute_scan", "execute_scan"):
            if truthy_pv(find_matching_pv(pvs, key)):
                return "running"
        if kind == "fly" and (
            pv_at_least_one(find_matching_pv(pvs, "wait"))
            or truthy_pv(find_matching_pv(pvs, "pause_signal"))
        ):
            return "pause"
        return "wait"

    def _scanrecord_paused(self, pvs: Mapping[str, Any], *, kind: str) -> bool:
        if kind == "fly":
            return (
                truthy_pv(find_matching_pv(pvs, "pause_signal"))
                or pv_at_least_one(find_matching_pv(pvs, "wait"))
            )
        return False

    def _inner_scan_point_count(self, snapshot: Mapping[str, Any]) -> float | None:
        scanrecord = self._scanrecord_device(snapshot)
        if not isinstance(scanrecord, Mapping):
            return None
        pvs = scanrecord.get("pvs")
        if not isinstance(pvs, Mapping):
            return None
        try:
            return float(pv_value_by_aliases(pvs, "inner.number_points"))
        except Exception:
            return None

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

    def _dwell_seconds(self, snapshot: Mapping[str, Any]) -> float | None:
        plan_args = snapshot.get("plan_args")
        if not isinstance(plan_args, Mapping):
            return None
        dwell_ms = plan_args.get("dwell_ms")
        if dwell_ms is None:
            dwell_ms = plan_args.get("dwell_time_ms")
        if dwell_ms is None:
            dwell_ms = plan_args.get("dwell_time")
        try:
            dwell_value = float(dwell_ms)
        except Exception:
            return None
        return max(0.0, dwell_value / 1000.0)

    def _detector_is_active(self, device_name: str, pvs: Mapping[str, Any]) -> bool:
        if device_name == "sis3820":
            return truthy_pv(find_matching_pv(pvs, "acquiring")) or pv_value(find_matching_pv(pvs, "current_channel")) is not None
        if device_name == "xrf":
            return truthy_pv(find_matching_pv(pvs, "fileplugin.capture", "capture")) or truthy_pv(
                find_matching_pv(pvs, "fileplugin.write_file", "write_file")
            )
        return truthy_pv(find_matching_pv(pvs, "cam.acquire", "acquire")) or truthy_pv(
            find_matching_pv(pvs, "fileplugin.capture", "capture")
        )

    def _detector_hung(self, device_name: str, snapshot: Mapping[str, Any]) -> bool:
        devices = snapshot.get("devices")
        if not isinstance(devices, Mapping):
            return False
        device = devices.get(device_name)
        if not isinstance(device, Mapping):
            return False
        pvs = device.get("pvs")
        if not isinstance(pvs, Mapping) or not self._detector_is_active(device_name, pvs):
            return False
        scanrecord = self._scanrecord_device(snapshot)
        if not isinstance(scanrecord, Mapping):
            return False
        scanrecord_pvs = scanrecord.get("pvs")
        if not isinstance(scanrecord_pvs, Mapping):
            return False
        scan_kind = self._scanrecord_kind(str(scanrecord.get("name") or ""), scanrecord)
        if self._scanrecord_paused(scanrecord_pvs, kind=scan_kind) or not self._scan_phase_waiting_for_detectors(snapshot):
            return False
        # ring_current = self._ring_current(snapshot)
        # if ring_current is None or ring_current <= 0:
        #     return False
        dwell_seconds = self._dwell_seconds(snapshot)
        inner_point_count = self._inner_scan_point_count(snapshot)
        if dwell_seconds is None or dwell_seconds <= 0 or inner_point_count is None or inner_point_count <= 0:
            return False
        now_ts = parse_timestamp(snapshot.get("timestamp"))
        if device_name == "sis3820":
            current_channel_pv = find_matching_pv(pvs, "current_channel")
            num_ch_used_pv = find_matching_pv(pvs, "num_ch_used")
            try:
                current_channel = float(pv_value(current_channel_pv))
                num_ch_used = float(pv_value(num_ch_used_pv))
            except Exception:
                return False
            if current_channel >= num_ch_used:
                return False
            signal = current_channel_pv
        else:
            signal = find_matching_pv(pvs, "fileplugin.capture", "capture", "cam.acquire", "acquire")
        if not isinstance(signal, Mapping):
            return False
        signal_ts = parse_timestamp(signal.get("timestamp"))
        if now_ts is None or signal_ts is None:
            return False
        age = (now_ts - signal_ts).total_seconds()
        timeout_seconds = max(_DETECTOR_STALE_SECONDS, _DETECTOR_TIMEOUT_FACTOR * inner_point_count * dwell_seconds)
        return age > timeout_seconds

    @staticmethod
    def _device_actions(device_name: str, role: str, *, recovering: bool = False) -> dict[str, Any]:
        recoverable = {"sis3820", "xrf", "tmm1"}
        if role == "detector" and device_name in recoverable:
            return {"recover": not recovering}
        return {}

    def enrich_device(self, device_name: str, device: Mapping[str, Any], snapshot: Mapping[str, Any]) -> dict[str, Any]:
        enriched = dict(device)
        role = self._infer_device_role(device_name, device)
        if role == "scanrecord":
            role = f"scanrecord_{self._scanrecord_kind(device_name, device)}"
        recovering = role == "detector" and is_detector_recovering(device_name)
        enriched["role"] = role
        enriched["state"] = "recovering" if recovering else "hung" if role == "detector" and self._detector_hung(device_name, snapshot) else "normal"
        enriched["health"] = self._evaluate_device_health(device_name, device, role, snapshot)
        enriched["summary"] = self._summarize_device(device_name, device, role, snapshot)
        enriched["actions"] = self._device_actions(device_name, role, recovering=recovering)
        return enriched

    def _evaluate_device_health(
        self,
        device_name: str,
        device: Mapping[str, Any],
        role: str,
        snapshot: Mapping[str, Any],
    ) -> str:
        pvs = device.get("pvs")
        if not isinstance(pvs, Mapping) or not pvs:
            return "warning"
        connected = 0
        degraded = 0
        for pv in pvs.values():
            if not isinstance(pv, Mapping):
                degraded += 1
                continue
            if pv.get("error"):
                degraded += 1
                continue
            if pv.get("connected"):
                connected += 1
            else:
                degraded += 1
        if connected == 0:
            return "error"
        if role == "ring":
            current = self._ring_current(snapshot)
            mode = self._ring_mode(snapshot).upper()
            if current is not None and current < 10 and "NO BEAM" in mode:
                return "error"
            if current is not None and current < 100:
                return "warning"
        if role.startswith("scanrecord") and self._scan_status(snapshot) == "pause":
            return "warning"
        if role == "detector" and self._detector_hung(device_name, snapshot):
            return "error"
        if degraded:
            return "warning"
        return "ok"

    def _summarize_device(
        self,
        device_name: str,
        device: Mapping[str, Any],
        role: str,
        snapshot: Mapping[str, Any],
    ) -> str:
        pvs = device.get("pvs")
        if not isinstance(pvs, Mapping):
            return "No PV data"
        if role in {"scanrecord", "scanrecord_fly", "scanrecord_step"}:
            status = self._scan_status(snapshot)
            point = pv_value_by_aliases(
                pvs,
                "inner.current_point",
                "current_point",
            )
            total = pv_value_by_aliases(
                pvs,
                "inner.number_points",
                "number_points",
            )
            suffix = " (fly)" if role == "scanrecord_fly" else " (step)" if role == "scanrecord_step" else ""
            if point is not None and total is not None:
                return f"Status: {status}{suffix}; point {point}/{total}"
            return f"Status: {status}{suffix}"
        if role == "motion":
            axes = []
            for axis, readback, setpoint in collect_axis_states(pvs):
                if readback is None and setpoint is None:
                    continue
                if setpoint is None:
                    axes.append(f"{axis}={readback}")
                else:
                    axes.append(f"{axis}={readback} (target {setpoint})")
            if axes:
                return ", ".join(axes)
        if role == "ring":
            current = self._ring_current(snapshot)
            mode = self._ring_mode(snapshot)
            parts = []
            if current is not None:
                parts.append(f"current={current}")
            if mode:
                parts.append(f"mode={mode}")
            if parts:
                return ", ".join(parts)
        if role == "detector":
            if is_detector_recovering(device_name):
                return "Detector recovery in progress"
            if self._detector_hung(device_name, snapshot):
                return "Detector hang detected; recovery is available"
            if device_name == "sis3820":
                current_channel = pv_value(find_matching_pv(pvs, "current_channel"))
                num_ch_used = pv_value(find_matching_pv(pvs, "num_ch_used"))
                if current_channel not in (None, "") and num_ch_used not in (None, ""):
                    return f"counting, current_channel={current_channel}/{num_ch_used}"
            acquiring = truthy_pv(find_matching_pv(pvs, "cam.acquire", "fileplugin.capture", "capture"))
            writing = truthy_pv(find_matching_pv(pvs, "fileplugin.write_file", "write_file"))
            filename = pv_value(find_matching_pv(pvs, "fileplugin.file_name", "file_name"))
            states = []
            if acquiring:
                states.append("acquiring")
            if writing:
                states.append("writing")
            if filename not in (None, ""):
                states.append(f"file={filename}")
            if states:
                return ", ".join(states)
        connected = sum(1 for pv in pvs.values() if isinstance(pv, Mapping) and pv.get("connected"))
        return f"{device_name}: {connected}/{len(pvs)} PVs connected"

    def summarize_activity(self, snapshot: Mapping[str, Any]) -> str:
        error = snapshot.get("error")
        if error:
            return str(error)
        plan_name = snapshot.get("plan_name")
        if not isinstance(plan_name, str) or not plan_name:
            return "idle"
        status = self._scan_status(snapshot)
        return f"{plan_name}: {status}"


def get_named_monitor_snapshot(
    device_names: list[str],
    *,
    manifest_path: str | None = None,
) -> dict[str, Any]:
    return _get_named_snapshot(
        device_names,
        manifest_path=manifest_path,
        default_manifest_path=_DEFAULT_MANIFEST_PATH,
        policy=S2IDDMonitorPolicy(),
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
        policy=S2IDDMonitorPolicy(),
    )

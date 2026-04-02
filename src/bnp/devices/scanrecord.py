from mic_common.devices.scan_record import NewScanRecord
from mic_common.devices.save_data import SaveDataMic
from mic_common.utils.device_utils import LoggingStageSigs, unstage_with_skip
from mic_common.utils.scan_monitor import execute_scan_2d, execute_scan_1d
from ophyd import Component, Device, EpicsSignal, EpicsSignalRO
from ophyd.device import Staged
import bluesky.plan_stubs as bps
import logging

logger = logging.getLogger(__name__)


class BNPScanRecord(Device):
    center = Component(EpicsSignal, ".P1CP")
    width = Component(EpicsSignal, ".P1WD")
    step_size = Component(EpicsSignal, ".P1SI")
    mode = Component(EpicsSignal, ".P1SM")
    abs_rel = Component(EpicsSignal, ".P1AR")

    det1 = Component(EpicsSignal, ".T1PV")
    det2 = Component(EpicsSignal, ".T2PV")
    det3 = Component(EpicsSignal, ".T3PV")
    det4 = Component(EpicsSignal, ".T4PV")

    execute_scan = Component(EpicsSignal, ".EXSC")
    scan_phase = Component(EpicsSignal, ".FAZE")
    number_points = Component(EpicsSignal, ".NPTS")
    current_point = Component(EpicsSignalRO, ".CPT")

    wait = Component(EpicsSignal, ".WAIT")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        original_stage_sigs = self.stage_sigs
        self.stage_sigs = LoggingStageSigs(original_stage_sigs, prefix=self.prefix)

    def stage_detTriggers(self, trigger_pvs: list[str]):
        for i, t_pv in enumerate(trigger_pvs):
            self.stage_sigs[f"det{i+1}"] = t_pv

    def unstage(self):
        unstage_with_skip(self, ["step_size"])
        return super().unstage()

    def config(
        self,
        center: float = None,
        width: float = None,
        step_size: float = None,
        mode: int = None,
        abs_rel: int = None,
        trigger_pvs: list = None,
    ):
        if self.connected:
            self.stage_sigs.clear()
            self.stage_sigs["center"] = center
            self.stage_sigs["width"] = width
            self.stage_sigs["step_size"] = step_size
            self.stage_sigs["mode"] = mode
            self.stage_sigs["abs_rel"] = abs_rel
            if trigger_pvs is not None:
                self.stage_detTriggers(trigger_pvs)
        else:
            logger.error(f"Scan record {self.prefix} is not connected")

class FlyScanRecord(Device):
    inner = Component(BNPScanRecord, ":scan1", kind="config", labels=("scanrecord", "inner"))
    outer = Component(BNPScanRecord, ":scan2", kind="config", labels=("scanrecord", "outer"))
    abort_signal = Component(EpicsSignal, ":AbortScans.PROC")

    def pad_detector_triggers(self, triggers_list, num_detectors = 4):
        return triggers_list + [''] * (num_detectors - len(triggers_list))

    def stage2Dfly(self, devices, sample, width, stepsize_x, height, stepsize_y):
        inner_triggers = [''] * 4
        outer_triggers = []
        dets_dict = {d.name: d for d in devices}

        xmap = dets_dict.get("xmap", None)
        sis3820 = dets_dict.get("sis3820", None)
        xp3 = dets_dict.get("xp3", None)
        eiger = dets_dict.get("eiger", None)

        try:
            yield from self.unstage2Dfly()
            logger.info("Unstage scanrecord if it is already staged")
        except Exception as e:
            logger.warning(f"Error unstaging scanrecord if it is already staged: {e}")

        outer_triggers.append(self.inner.execute_scan.pvname)
        if eiger is not None:
            outer_triggers.append(eiger.fileplugin.capture.pvname.replace("_RBV", ""))
            outer_triggers.append(eiger.cam.acquire.pvname.replace("_RBV", ""))
            outer_triggers.append("")

        self.inner.config(
            center = round(sample.x.piezo.position, 2),
            width = round(width, 2),
            step_size = round(stepsize_x, 2),
            mode = 2,     # 0: "LINEAR", 1: "TABLE", 2: "FLY"
            abs_rel = 0 , # 0: "ABSOLUTE", 1: "RELATIVE"
            # trigger_pvs = inner_triggers,
        )

        self.outer.config(
            center = round(sample.y.piezo.position, 2),
            width = round(height, 2),
            step_size = round(stepsize_y, 2),
            mode = 0, # 0: "LINEAR", 1: "TABLE", 2: "FLY"
            abs_rel = 0, # 0: "ABSOLUTE", 1: "RELATIVE"
            trigger_pvs = outer_triggers,
        )

        self.inner.stage()
        yield from bps.sleep(0.1)
        self.outer.stage()
        yield from bps.sleep(0.1)

    def unstage2Dfly(self):
        if self.inner._staged == Staged.yes or self.outer._staged == Staged.partially:
            logger.info("Inner scanrecord is already staged, unstaging ... ...")
            self.inner.unstage()
            yield from bps.sleep(0.1)
        if self.outer._staged == Staged.yes or self.outer._staged == Staged.partially:
            logger.info("Outer scanrecord is already staged, unstaging ... ...")
            self.outer.unstage()
            yield from bps.sleep(0.1)

    def execute2Dfly(self, scan_name="", sample=None, print_outter_msg=True):
        yield from execute_scan_2d(
            self.inner, 
            self.outer, 
            self.abort_signal, 
            sample=sample, 
            scan_name=scan_name, 
            print_outter_msg=print_outter_msg
        )

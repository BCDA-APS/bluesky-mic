from mic_common.devices.scan_record import NewScanRecord
from mic_common.devices.save_data import SaveDataMic
from mic_common.utils.scan_monitor import execute_scan_2d, execute_scan_1d
from ophyd import Component, Device, EpicsSignal
from ophyd.device import Staged
import bluesky.plan_stubs as bps
import logging

logger = logging.getLogger(__name__)


class FlyScanRecord(Device):
    inner = Component(NewScanRecord, ":FscanH", kind="config", labels=("scanrecord", "inner"))
    outer = Component(NewScanRecord, ":Fscan1", kind="config", labels=("scanrecord", "outer"))
    abort_signal = Component(EpicsSignal, ":FAbortScans.PROC")
    pause_signal = Component(EpicsSignal, ":FscanPause.VAL")
    wait = Component(EpicsSignal, ":Fscan1.WAIT")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def stage2Dfly(self, devices, sample, fscanh_samx, width, stepsize_x, height, stepsize_y):
        inner_triggers = []
        outer_triggers = []
        dets_dict = {d.name: d for d in devices}

        xrf = dets_dict.get("xrf", None)
        sis3820 = dets_dict.get("sis3820", None)
        preamp1 = dets_dict.get("tmm1", None)

        try:
            yield from self.unstage2Dfly()
            logger.info("Unstage scanrecord if it is already staged")
        except Exception as e:
            logger.warning(f"Error unstaging scanrecord if it is already staged: {e}")

        if all([xrf is not None, sis3820 is not None]):
            inner_triggers.append(xrf.fileplugin.capture.pvname.replace("_RBV", ""))
            inner_triggers.append(xrf.cam.erase_start.pvname)
            inner_triggers.append(sis3820.erase_start.pvname)
        else:
            inner_triggers = []

        if preamp1 is not None:
            outer_triggers.append(preamp1.fileplugin.capture.pvname.replace("_RBV", ""))
            outer_triggers.append(preamp1.cam.acquire.pvname)
            outer_triggers.append(self.inner.execute_scan.pvname)
        else:
            outer_triggers.append(self.inner.execute_scan.pvname)

        self.inner.config(
            positioner_setpoint=f"{fscanh_samx.pvname}",
            scanmode=2,  # 0: "LINEAR", 1: "TABLE", 2: "FLY"
            center=round(sample.x.position, 2),
            width=round(width, 2),
            stepsize=round(stepsize_x, 2),
            trigger_pvs=inner_triggers,
        )

        self.outer.config(
            positioner_setpoint=sample.y.user_setpoint.pvname,
            positioner_readback=sample.y.user_readback.pvname,
            rel_abs_motion=1,  # 0: "ABSOLUTE", 1: "RELATIVE"
            center=0,
            width=round(height, 2),
            stepsize=round(stepsize_y, 2),
            trigger_pvs=outer_triggers,
        )

        self.inner.stage()
        yield from bps.sleep(0.1)
        self.outer.stage()
        yield from bps.sleep(0.1)

    def unstage2Dfly(self):
        if self.inner._staged == Staged.yes or self.inner._staged == Staged.partially:
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



class StepScanRecord(Device):
    inner = Component(NewScanRecord, ":scan1", kind="config", labels=("scanrecord", "inner"))
    outer = Component(NewScanRecord, ":scan2", kind="config", labels=("scanrecord", "outer"))
    detloop = Component(NewScanRecord, ":scanH", kind="config", labels=("scanrecord", "detloop"))
    abort_signal = Component(EpicsSignal, ":AbortScans.PROC")
    num_det_triggers = 4

    @staticmethod
    def _resolve_attr_path(obj, path):
        cur = obj
        for part in path.split("."):
            cur = getattr(cur, part, None)
            if cur is None:
                return None
        return cur

    def _skip_restore_fields_on_unstage(self, scan, fields_to_skip):
        """Remove selected fields from stage restore for this unstage call only."""
        for field in fields_to_skip:
            scan.stage_sigs.pop(field, None)

        if not getattr(scan, "_original_vals", None):
            return

        signal_objs = []
        for field in fields_to_skip:
            sig = self._resolve_attr_path(scan, field)
            if sig is not None:
                signal_objs.append(sig)

        if not signal_objs:
            return

        keys_to_remove = []
        for key in list(scan._original_vals.keys()):
            for sig in signal_objs:
                if key is sig or (hasattr(key, "name") and hasattr(sig, "name") and key.name == sig.name):
                    keys_to_remove.append(key)
                    break

        for key in keys_to_remove:
            scan._original_vals.pop(key, None)

    def stage1Dstep(self, devices, scaler_count, positioner, width, center, stepsize_x):
        dets_dict = {d.name: d for d in devices}

        xrf = dets_dict.get("xrf", None)
        preamp1 = dets_dict.get("tmm1", None)

        det_triggers = []
        if xrf is not None:
            det_triggers.append(xrf.cam.erase_start.pvname)
        if preamp1 is not None:
            det_triggers.append(preamp1.cam.acquire.pvname)
        det_triggers += [''] * (self.num_det_triggers - len(det_triggers))

        inner_triggers = []
        inner_triggers.append(scaler_count.pvname)
        inner_triggers.append(self.detloop.execute_scan.pvname)
        inner_triggers += [''] * (self.num_det_triggers - len(inner_triggers))

        yield from self.unstage1Dstep()
        self.inner.config(
            positioner_setpoint=positioner.user_setpoint.pvname,
            positioner_readback=positioner.user_readback.pvname,
            scanmode=0,  # 0: "LINEAR", 1: "TABLE", 2: "FLY"
            rel_abs_motion=1,  # 0: "ABSOLUTE", 1: "RELATIVE"
            center=center,
            width=round(width, 2),
            stepsize=round(stepsize_x, 5),
            trigger_pvs=inner_triggers,
        )
        self.detloop.config(
            positioner_setpoint="",
            positioner_readback="",
            scanmode=0,  # 0: "LINEAR", 1: "TABLE", 2: "FLY"
            rel_abs_motion=0,  # 0: "ABSOLUTE", 1: "RELATIVE"
            center=0,
            width=0,
            stepsize=0,
            trigger_pvs=det_triggers,
        )

        self.inner.stage()
        yield from bps.sleep(0.2)
        self.detloop.stage()
        yield from bps.sleep(0.2)

    def stage1Dstep_TabelMode(self, devices, scaler_count, positioner, setpoint_list):
        dets_dict = {d.name: d for d in devices}

        xrf = dets_dict.get("xrf", None)
        preamp1 = dets_dict.get("tmm1", None)

        det_triggers = []
        if xrf is not None:
            det_triggers.append(xrf.cam.erase_start.pvname)
        if preamp1 is not None:
            det_triggers.append(preamp1.cam.acquire.pvname)
        det_triggers += [''] * (self.num_det_triggers - len(det_triggers))

        inner_triggers = []
        inner_triggers.append(scaler_count.pvname)
        inner_triggers.append(self.detloop.execute_scan.pvname)
        inner_triggers += [''] * (self.num_det_triggers - len(inner_triggers))

        yield from self.unstage1Dstep()
        self.inner.config(
            positioner_setpoint=positioner.user_setpoint.pvname,
            positioner_readback=positioner.user_readback.pvname,
            scanmode=1,  # 0: "LINEAR", 1: "TABLE", 2: "FLY"
            rel_abs_motion=0,  # 0: "ABSOLUTE", 1: "RELATIVE"
            setpoint_list=setpoint_list,
            trigger_pvs=inner_triggers,
            num_points=len(setpoint_list),
        )
        self.detloop.config(
            positioner_setpoint="",
            positioner_readback="",
            scanmode=0,  # 0: "LINEAR", 1: "TABLE", 2: "FLY"
            rel_abs_motion=0,  # 0: "ABSOLUTE", 1: "RELATIVE"
            center=0,
            width=0,
            stepsize=0,
            trigger_pvs=det_triggers,
        )

        self.inner.stage()
        yield from bps.sleep(0.2)
        self.detloop.stage()
        yield from bps.sleep(0.2)

    def unstage1Dstep(self):
        if self.inner._staged == Staged.yes or self.inner._staged == Staged.partially:
            logger.info("Inner scanrecord is already staged, unstaging ... ...")
            self._skip_restore_fields_on_unstage(
                self.inner,
                [
                    "positioners.p1.setpoint_pv",
                    "positioners.p1.readback_pv",
                    "positioners.p1.mode",
                    "positioners.p1.abs_rel",
                    "positioners.p1.center",
                    "positioners.p1.width",
                    "positioners.p1.step_size",
                    "triggers.t1.trigger_pv",
                    "triggers.t2.trigger_pv",
                    "triggers.t3.trigger_pv",
                    "triggers.t4.trigger_pv",
                ],
            )
            self.inner.unstage()
            yield from bps.sleep(0.2)

        if self.detloop._staged == Staged.yes or self.detloop._staged == Staged.partially:
            logger.info("Detloop scanrecord is already staged, unstaging ... ...")
            self.detloop.unstage()


    def execute1Dstep(self, scan_name=""):
        yield from execute_scan_1d(self.inner, 
                                   scan_name=scan_name, 
                                   abort_signal=self.abort_signal)


class CombinedScanRecord(Device):
    fly = Component(FlyScanRecord, "", kind="config", labels=("scanrecord", "fly"))
    step = Component(StepScanRecord, "", kind="config", labels=("scanrecord", "step"))
    savedata = Component(SaveDataMic, ":saveData_", kind="config", labels=("savedata"))

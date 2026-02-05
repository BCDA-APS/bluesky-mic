from mic_common.devices.scan_record import NewScanRecord
from mic_common.devices.save_data import SaveDataMic
from mic_common.utils.scan_monitor import execute_scan_2d, execute_scan_1d
from ophyd import Component, Device
from ophyd.device import Staged
import bluesky.plan_stubs as bps
import logging

logger = logging.getLogger(__name__)


class FlyScanRecord(Device):
    inner = Component(NewScanRecord, ":FscanH", kind="config", labels=("scanrecord", "inner"))
    outer = Component(NewScanRecord, ":Fscan1", kind="config", labels=("scanrecord", "outer"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outer.pause = self.pause
        self.outer.resume = self.resume

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
            self.inner, self.outer, sample=sample, scan_name=scan_name, print_outter_msg=print_outter_msg
        )


class StepScanRecord(Device):
    inner = Component(NewScanRecord, ":scan1", kind="config", labels=("scanrecord", "inner"))
    outer = Component(NewScanRecord, ":scan2", kind="config", labels=("scanrecord", "outer"))
    detloop = Component(NewScanRecord, ":scanH", kind="config", labels=("scanrecord", "detloop"))

    def stage1Dstep(self, devices, scaler_count, positioner, width, stepsize_x):
        dets_dict = {d.name: d for d in devices}

        xrf = dets_dict.get("xrf", None)
        preamp1 = dets_dict.get("tmm1", None)

        det_triggers = []
        if preamp1 is not None:
            det_triggers.append(preamp1.cam.acquire.pvname)
        if xrf is not None:
            det_triggers.append(xrf.cam.erase_start.pvname)
        det_triggers.append(scaler_count.pvname)
        det_triggers.append(self.detloop.execute_scan.pvname)

        self.unstage1Dstep()
        self.inner.config(
            positioner_setpoint=positioner.user_setpoint.pvname,
            positioner_readback=positioner.user_readback.pvname,
            scanmode=0,  # 0: "LINEAR", 1: "TABLE", 2: "FLY"
            rel_abs_motion=1,  # 0: "ABSOLUTE", 1: "RELATIVE"
            center=0,
            width=round(width, 2),
            stepsize=round(stepsize_x, 2),
            trigger_pvs=det_triggers,
        )

        self.inner.stage()
        yield from bps.sleep(0.2)


    def unstage1Dstep(self):
        if self.inner._staged == Staged.yes:
            logger.info("Inner scanrecord is already staged, unstaging ... ...")
            self.inner.unstage()
            yield from bps.sleep(0.2)

    def execute1Dstep(self, scan_name=""):
        yield from execute_scan_1d(self.inner, scan_name=scan_name)

    # def stage2Dstep(self):
    #     self.step.inner.stage()
    #     yield from bps.sleep(0.2)
    #     self.step.outer.stage()
    #     yield from bps.sleep(0.2)

    # def unstage2Dstep(self):
    #     self.step.inner.unstage()
    #     yield from bps.sleep(0.2)
    #     self.step.outer.unstage()
    #     yield from bps.sleep(0.2)


class CombinedScanRecord(Device):
    fly = Component(FlyScanRecord, "", kind="config", labels=("scanrecord", "fly"))
    step = Component(StepScanRecord, "", kind="config", labels=("scanrecord", "step"))
    savedata = Component(SaveDataMic, ":saveData_", kind="config", labels=("savedata"))

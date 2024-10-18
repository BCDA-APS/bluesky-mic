__all__ = """
    tmm1
""".split()

import logging

import bluesky.plan_stubs as bps
from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal

from ..utils.config_loaders import iconfig

logger = logging.getLogger(__name__)
logger.info(__file__)
# test


class TetraMM(Device):
    Acquire = Component(EpicsSignal, "Acquire")
    AcquireMode = Component(EpicsSignal, "AcquireMode")
    Range = Component(EpicsSignal, "Range")
    ValuesPerRead = Component(EpicsSignal, "ValuesPerRead")
    AveragingTime = Component(EpicsSignal, "AveragingTime")
    FastAveragingTime = Component(EpicsSignal, "FastAveragingTime")
    FastAverageScan_scan = Component(EpicsSignal, "FastAverageScan.SCAN")
    EmptyFreeList = Component(EpicsSignal, "EmptyFreeList")
    TriggerMode = Component(EpicsSignal, "TriggerMode")
    NumAcquire = Component(EpicsSignal, "NumAcquire")
    Capture = Component(EpicsSignal, "netCDF1:Capture")
    FilePath = Component(EpicsSignal, "netCDF1:FilePath", string=True)
    FileName = Component(EpicsSignal, "netCDF1:FileName", string=True)
    NumCapture = Component(EpicsSignal, "netCDF1:NumCapture")
    FileNumber = Component(EpicsSignal, "netCDF1:FileNumber")
    FileTemplate = Component(EpicsSignal, "netCDF1:FileTemplate", string=True)
    AutoIncrement = Component(EpicsSignal, "netCDF1:AutoIncrement")
    AutoSave = Component(EpicsSignal, "netCDF1:AutoSave")
    WriteFile = Component(EpicsSignal, "netCDF1:WriteFile")
    FileWriteMode = Component(EpicsSignal, "netCDF1:FileWriteMode")
    WriteStatus = Component(EpicsSignal, "netCDF1:WriteStatus")
    FilePathExists_RBV = Component(EpicsSignal, "netCDF1:FilePathExists_RBV")

    def setup_tetramm(
        self,
        npts,
        sample_name,
        save_path,
        dwell_time,
        trigger_mode,
        scanNumber,
        reset_counter=False,
    ):
        print("in setup_tetramm function")
        self.wait_for_connection()
        # yield from run_blocking_function(pm1.abort) # TODO: re-implement reset function for profile move
        yield from bps.sleep(0.2)  # arbitrary wait for EPICS to finish the reset.

        if self.Capture.value == 1:
            yield from bps.mv(self.Capture, 0)
        if self.Acquire.value == 1:
            yield from bps.mv(self.Acquire, 0)
        if reset_counter:
            yield from bps.mv(self.FileNumber, 0)

        yield from bps.mv(
            self.TriggerMode,
            trigger_mode,
            self.NumAcquire,
            npts,
            self.NumCapture,
            npts,
            self.EmptyFreeList,
            1,
            self.ValuesPerRead,
            int(100000 * dwell_time - 1),  # 100,000/dwell_time(ms)
            self.AveragingTime,
            dwell_time,
            self.FastAveragingTime,
            dwell_time,
            self.AutoIncrement,
            0,
            self.FileNumber,
            scanNumber,
            self.AutoSave,
            1,
            self.FileWriteMode,
            2,
            self.FilePath,
            save_path,
            self.FileName,
            sample_name,
            self.FileTemplate,
            "%s%s_%05d.nc",
            self.Capture,
            1,
            self.Acquire,
            1,
        )


pv1 = iconfig.get("DEVICES")["TETRAMM1"]
tmm1 = TetraMM(pv1, name="tmm1")

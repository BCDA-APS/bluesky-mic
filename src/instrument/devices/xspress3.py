
__all__ = """
    xp3
""".split()

from ..utils.iconfig_loader import iconfig
from ophyd import Device, EpicsSignal, Component
import bluesky.plan_stubs as bps
import logging
logger = logging.getLogger(__name__)
logger.info(__file__)

class Xspress3(Device):
    ERASE = Component(EpicsSignal, 'det1:ERASE')
    Acquire = Component(EpicsSignal, 'det1:Acquire')
    AcquireTime = Component(EpicsSignal, 'det1:AcquireTime')
    NumImages = Component(EpicsSignal, 'det1:NumImages')
    ArrayCounter_RBV = Component(EpicsSignal, 'det1:ArrayCounter_RBV')
    EraseOnStart = Component(EpicsSignal, 'det1:EraseOnStart')
    DetectorState_RBV = Component(EpicsSignal, 'det1:DetectorState_RBV')
    TriggerMode = Component(EpicsSignal, 'det1:TriggerMode')
    EnableCallbacks = Component(EpicsSignal, 'Pva1:EnableCallbacks')
    Capture = Component(EpicsSignal, 'HDF1:Capture')
    FilePath = Component(EpicsSignal, 'HDF1:FilePath', string=True)
    FileName = Component(EpicsSignal, 'HDF1:FileName', string=True)
    FileNumber = Component(EpicsSignal, 'HDF1:FileNumber')
    FileWriteMode = Component(EpicsSignal, 'HDF1:FileWriteMode')
    FileTemplate = Component(EpicsSignal, 'HDF1:FileTemplate', string=True)
    AutoIncrement = Component(EpicsSignal, 'HDF1:AutoIncrement')
    AutoSave = Component(EpicsSignal, 'HDF1:AutoSave')
    NumCaptured_RBV = Component(EpicsSignal, 'HDF1:NumCaptured_RBV')

    def setup_xspress3(self, npts, sample_name, save_path, dwell_time, trigger_mode, scanNumber, reset_counter=False):
        print("in setup_xspress3 function")
        self.wait_for_connection()
        yield from bps.sleep(0.2)  # arbitrary wait for EPICS to finish the reset.

        if self.Capture.value==1:
            yield from bps.mv(self.Capture, 0)
        if self.Acquire.value==1:
            yield from bps.mv(self.Acquire, 0)
        if reset_counter: 
            yield from bps.mv(self.FileNumber, 0)

        yield from bps.mv(
            self.ERASE, 1,
            self.NumImages, npts,
            self.AcquireTime, dwell_time,
            self.EraseOnStart, 0,
            self.TriggerMode, trigger_mode, 
            self.EnableCallbacks, 1, 
            self.AutoIncrement, 0,
            self.FileNumber, scanNumber,
            self.AutoSave, 1,
            self.FileWriteMode, 2,
            self.FilePath, save_path,
            self.FileName, sample_name,
            self.FileTemplate, f"%s%s_%05d.h5",
            self.Capture, 1,
            self.Acquire, 1, 
            )
        
pv = iconfig.get("DEVICES")["XSPRESS3"]
xp3 = Xspress3(pv, name="xp3") 

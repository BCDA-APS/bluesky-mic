
__all__ = """
    xp3
    setup_xspress3
""".split()

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

def setup_xspress3(xp3, npts, sample_name, save_path, dwell_time, trigger_mode, scanNumber, reset_counter=False):
    print("in setup_xspress3 function")
    xp3.wait_for_connection()
    yield from bps.sleep(0.2)  # arbitrary wait for EPICS to finish the reset.

    if xp3.Capture.value==1:
        yield from bps.mv(xp3.Capture, 0)
    if xp3.Acquire.value==1:
        yield from bps.mv(xp3.Acquire, 0)
    if reset_counter: 
        yield from bps.mv(xp3.FileNumber, 0)

    yield from bps.mv(
        xp3.ERASE, 1,
        xp3.NumImages, npts,
        xp3.AcquireTime, dwell_time,
        xp3.EraseOnStart, 0,
        xp3.TriggerMode, trigger_mode, 
        xp3.EnableCallbacks, 1, 
        xp3.AutoIncrement, 0,
        xp3.FileNumber, scanNumber,
        xp3.AutoSave, 1,
        xp3.FileWriteMode, 2,
        xp3.FilePath, save_path,
        xp3.FileName, sample_name,
        xp3.FileTemplate, f"%s%s_%05d.h5",
        xp3.Capture, 1,
        xp3.Acquire, 1, 
        )
xp3 = Xspress3("XSP3_1Chan:", name="tmm") 

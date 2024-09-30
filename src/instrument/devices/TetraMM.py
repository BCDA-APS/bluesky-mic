
__all__ = """
    tmm
    setup_tetramm
""".split()

from ophyd import Device, EpicsSignal, Component
import bluesky.plan_stubs as bps
import logging
logger = logging.getLogger(__name__)
logger.info(__file__)
#test

class TetraMM(Device):
    Acquire = Component(EpicsSignal, 'Acquire')
    AcquireMode = Component(EpicsSignal, 'AcquireMode')
    Range = Component(EpicsSignal, 'Range')
    ValuesPerRead = Component(EpicsSignal, 'ValuesPerRead')
    AveragingTime = Component(EpicsSignal, 'AveragingTime')
    FastAveragingTime = Component(EpicsSignal, 'FastAveragingTime')
    FastAverageScan_scan = Component(EpicsSignal, 'FastAverageScan.SCAN')
    EmptyFreeList = Component(EpicsSignal, 'EmptyFreeList')
    TriggerMode = Component(EpicsSignal, 'TriggerMode')
    NumAcquire = Component(EpicsSignal, 'NumAcquire')
    Capture = Component(EpicsSignal, 'netCDF1:Capture')
    FilePath = Component(EpicsSignal, 'netCDF1:FilePath', string=True)
    FileName = Component(EpicsSignal, 'netCDF1:FileName', string=True)
    NumCapture = Component(EpicsSignal, 'netCDF1:NumCapture')
    FileNumber = Component(EpicsSignal, 'netCDF1:FileNumber')
    FileTemplate = Component(EpicsSignal, 'netCDF1:FileTemplate', string=True)
    AutoIncrement = Component(EpicsSignal, 'netCDF1:AutoIncrement')
    AutoSave = Component(EpicsSignal, 'netCDF1:AutoSave')
    WriteFile = Component(EpicsSignal, 'netCDF1:WriteFile')
    FileWriteMode = Component(EpicsSignal, 'netCDF1:FileWriteMode')
    WriteStatus = Component(EpicsSignal, 'netCDF1:WriteStatus')
    FilePathExists_RBV = Component(EpicsSignal, 'netCDF1:FilePathExists_RBV')
    
def setup_tetramm(tmm, npts, sample_name, save_path, dwell_time, trigger_mode, scanNumber, reset_counter=False):
    print("in setup_tetramm function")
    tmm.wait_for_connection()
    # yield from run_blocking_function(pm1.abort) # TODO: re-implement reset function for profile move
    yield from bps.sleep(0.2)  # arbitrary wait for EPICS to finish the reset.
    
    if tmm.Capture.value==1:
        yield from bps.mv(tmm.Capture, 0)
    if tmm.Acquire.value==1:
        yield from bps.mv(tmm.Acquire, 0)
    if reset_counter: 
        yield from bps.mv(tmm.FileNumber, 0)

    yield from bps.mv(
        tmm.TriggerMode, trigger_mode,
        tmm.NumAcquire, npts,
        tmm.NumCapture, npts, 
        tmm.EmptyFreeList, 1,
        tmm.ValuesPerRead, int(100000*dwell_time - 1), #100,000/dwell_time(ms)
        tmm.AveragingTime, dwell_time, 
        tmm.FastAveragingTime, dwell_time,
        tmm.AutoIncrement, 0,
        tmm.FileNumber, scanNumber,
        tmm.AutoSave, 1,
        tmm.FileWriteMode, 2,
        tmm.FilePath, save_path,
        tmm.FileName, sample_name,
        tmm.FileTemplate, f"%s%s_%05d.nc",
        tmm.Capture, 1,
        tmm.Acquire, 1, 
        )

tmm = TetraMM("2idsft:TetrAMM1:", name="tmm") 

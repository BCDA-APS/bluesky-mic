
__all__ = """
    xp3
""".split()

from ..utils.iconfig_loader import iconfig
from ophyd import Device, EpicsSignal, Component
import bluesky.plan_stubs as bps
import logging
import os
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
    Capture_RBV = Component(EpicsSignal, 'HDF1:Capture_RBV')
    FilePath = Component(EpicsSignal, 'HDF1:FilePath', string=True)
    FileName = Component(EpicsSignal, 'HDF1:FileName', string=True)
    FileNumber = Component(EpicsSignal, 'HDF1:FileNumber')
    FileWriteMode = Component(EpicsSignal, 'HDF1:FileWriteMode')
    FileTemplate = Component(EpicsSignal, 'HDF1:FileTemplate', string=True)
    WriteFile_RBV = Component(EpicsSignal, 'HDF1:WriteFile_RBV', string=True)
    AutoIncrement = Component(EpicsSignal, 'HDF1:AutoIncrement')
    AutoSave = Component(EpicsSignal, 'HDF1:AutoSave')
    NumCaptured_RBV = Component(EpicsSignal, 'HDF1:NumCaptured_RBV')

    next_filepath = None
    next_scan_name = None
    connected = False
    status = "Idle"

    def get_formatted_scan_num(self):
        file_format = self.FileTemplate.get()
        file_path = self.FilePath.get() + "/"
        file_name = self.FileName.get()
        file_number = self.FileNumber.get()
        self.next_filepath = file_format % (file_path, file_name, file_number)
        self.next_scan_name = os.path.basename(self.next_filepath)

    def update_status(self):
        self.status = self.DetectorState_RBV.get(as_string=True)

    def initialize(self, file_path=None, file_prefix=None, file_number=None,
                      file_format="%s%s_%05d.h5"):
        
        logger.info("Initialzing xspress3 hardware for XRF data collection")
        try:
            self.wait_for_connection()
            self.connected = True
        except Exception as e:
            logger.exception(f"{e}")
            logger.error("Not able to connect to xspress3 device")

        if self.connected:
            if file_path is not None:
                yield from bps.mv(self.FilePath, file_path)
                logger.info(f"Updating {self.FilePath.pvname} to {file_path}")
            if file_prefix is not None:
                yield from bps.mv(self.FileName, file_prefix)
                logger.info(f"Updating {self.FileName.pvname} to {file_prefix}")
            if file_number is not None:
                yield from bps.mv(self.FileNumber, file_number)
                logger.info(f"Updating {self.FileNumber.pvname} to {file_number}")
            
            yield from bps.mv(self.EraseOnStart, 0)
            logger.info(f"Updating {self.EraseOnStart.pvname} to 0")
            yield from bps.mv(self.FileTemplate, file_format)
            logger.info(f"Updating {self.FileTemplate.pvname} to {file_format}")
            self.update_status()

    def setup_xspress3(self, npts, dwell_time, trigger_mode = 3):

        if all([self.status != "Idle"]):


        if self.Capture_RBV.get():
            yield from bps.mv(self.Capture, 1)
            logger.info(f"Arming xspress3 {self.Capture.pvname} to {1}")
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
            # self.FilePath, save_path,
            # self.FileName, sample_name,
            self.FileTemplate, f"%s%s_%05d.h5",
            self.Capture, 1,
            self.Acquire, 1, 
            )
        
pv = iconfig.get("DEVICES")["XSPRESS3"]
xp3 = Xspress3(pv, name="xp3") 

from apsbits.utils.controls_setup import oregistry
from apstools.devices import CamMixin_V34
from ophyd import ADComponent
from ophyd import Component
from ophyd import EpicsSignal
from ophyd import EpicsSignalWithRBV
from ophyd.areadetector import Xspress3DetectorCam
from ophyd.areadetector.plugins import HDF5Plugin


class VortexDetectorCam(CamMixin_V34, Xspress3DetectorCam):
    trigger_mode = Component(EpicsSignalWithRBV, "TriggerMode", kind="config")
    erase_on_start = Component(EpicsSignal, "EraseOnStart", string=True, kind="config")
    soft_trigger = ADComponent(EpicsSignal, "SoftTrigger")

    # Removed
    offset = None
    num_exposures = None
    acquire_period = None


class MicHDF5(HDF5Plugin):
    def __init__(self, *args, **kwargs):
        """Initialize MicHDF5."""
        super().__init__(*args, **kwargs)

    def stage(self):
        savedata = oregistry["savedata"]

        file_path = savedata.generate_det_path(self.parent.name.upper())
        base_name = savedata.base_name.get()
        scan_number = savedata.next_scan_number.get()
        file_name = base_name + f"{scan_number:04d}"

        self.capture.put(0)
        self.file_path.put(file_path)
        self.file_name.put(file_name)
        self.auto_increment.put(1)
        self.file_number.put(1)
        self.file_write_mode.put(2)

        super().stage()

    def unstage(self):
        self.capture.put(0)
        super().unstage()

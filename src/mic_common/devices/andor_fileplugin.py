from apsbits.core.instrument_init import oregistry
from apstools.devices import CamMixin_V34
from ophyd import ADComponent
from ophyd import Component
from ophyd import EpicsSignal
from ophyd import EpicsSignalWithRBV
from ophyd.areadetector import Xspress3DetectorCam
from ophyd.areadetector.plugins import HDF5Plugin
from ophyd.areadetector.plugins import StatsPlugin
from ophyd.areadetector.plugins import PluginBase

from isn.utils.run_engine import RE


class WindowsHDF5(HDF5Plugin):
    # Shared micdata mount roots for a Windows-hosted IOC. Injected from
    # iconfig (WINDOWS_STORAGE) at startup; see isn/startup.py.
    linux_root = ""
    windows_root = ""

    def __init__(self, *args, **kwargs):
        """Initialize WindowsHDF5."""
        super().__init__(*args, **kwargs)

    def stage(self):
        savedata = oregistry["savedata"]

        file_path = savedata.generate_det_path_windows(
            self.parent.name.upper(), self.linux_root, self.windows_root
        )
        base_name = savedata.base_name.get()
        # scan_number = savedata.next_scan_number.get()
        try:
            scan_number = RE.md['scan_id']+1
        except:
            scan_number = 1
        file_name = base_name + f"{scan_number:04d}"

        # self.capture.put(0)
        self.file_template.put("%s%s_%3.5d.h5")
        self.file_path.put(file_path)
        self.file_name.put(file_name)
        self.auto_increment.put(1)
        self.file_number.put(1)
        self.file_write_mode.put(2)

        super().stage()

    def unstage(self):
        self.capture.put(0)
        super().unstage()

class MicStatsPlugin(StatsPlugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total.kind = 'hinted'

    _default_read_attrs = ('total',)


class MicCodecPlugin(PluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.codec_kind = 'config'

    def stage(self):
        super().stage()

    

"""
Created on Jan 15 2024

4-elm XMAP

@author: yluo (grace227)
"""

# from apstools.devices import Struck3820
from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO

from ..devices.utils import mode_setter
from ..devices.utils import value_setter


class XMAP(Device):
    start_all = Component(EpicsSignal, "StartAll")
    stop_all = Component(EpicsSignal, "StopAll")
    erase_start = Component(EpicsSignal, "EraseStart")
    erase_all = Component(EpicsSignal, "EraseAll")
    acquiring = Component(EpicsSignalRO, "Acquiring", string=True)
    collection_mode = Component(EpicsSignal, "CollectMode")
    preset_mode = Component(EpicsSignal, "PresetMode")
    elapsed_real_time = Component(EpicsSignalRO, "ElapsedReal")
    preset_real_time = Component(EpicsSignal, "PresetReal")
    elapsed_live_time = Component(EpicsSignalRO, "ElapsedLive")
    preset_live_time = Component(EpicsSignal, "PresetLive")
    status_rate = Component(EpicsSignal, "StatusAll.SCAN")
    read_rate = Component(EpicsSignal, "ReadAll.SCAN")
    pixels_per_run = Component(EpicsSignal, "PixelsPerRun")

    # XMAP initialization before step scan
    def stepscan_before(self):
        yield from self.set_collection_mode("MCA SPECTRA")
        yield from self.set_preset_mode("Real Time")
        yield from self.set_status_rate("Passive")
        yield from self.set_read_rate("Passive")

    # XMAP initialization after step scan
    def stepscan_after(self):
        yield from self.set_status_rate(".2 SECOND")
        yield from self.set_read_rate(".2 SECOND")

    # XMAP initialization before fly scan
    def flyscan_before(self, num_pts):
        yield from self.set_collection_mode("MCA MAPPING")
        yield from self.set_pixels_per_run(num_pts)

    def flyscan_after(self):
        yield from self.set_collection_mode("MCA SPECTRA")

    @mode_setter("preset_mode")
    def set_preset_mode(mode):
        pass

    @mode_setter("collection_mode")
    def set_collection_mode(mode):
        pass

    @mode_setter("status_rate")
    def set_status_rate(rate):
        pass

    @mode_setter("read_rate")
    def set_read_rate(rate):
        pass

    @value_setter("preset_real_time")
    def set_real_time(real_time):
        pass

    @value_setter("preset_live_time")
    def set_live_time(live_time):
        pass

    @value_setter("pixels_per_run")
    def set_pixels_per_run(numpts):
        pass

    @value_setter("stop_all")
    def set_stop_all(stop_all):
        pass

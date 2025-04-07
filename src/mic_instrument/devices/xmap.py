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

from ..utils.device_utils import mode_setter
from ..utils.device_utils import value_setter


class XMAP(Device):
    """4-element XMAP device for X-ray spectroscopy."""

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

    def stepscan_before(self):
        """Initialize XMAP before step scan."""
        yield from self.set_collection_mode("MCA SPECTRA")
        yield from self.set_preset_mode("Real Time")
        yield from self.set_status_rate("Passive")
        yield from self.set_read_rate("Passive")

    def stepscan_after(self):
        """Configure XMAP after step scan."""
        yield from self.set_status_rate(".2 SECOND")
        yield from self.set_read_rate(".2 SECOND")

    def flyscan_before(self, num_pts):
        """Initialize XMAP before fly scan.

        Parameters:
            num_pts (int): Number of points to collect.
        """
        yield from self.set_collection_mode("MCA MAPPING")
        yield from self.set_pixels_per_run(num_pts)

    def flyscan_after(self):
        """Configure XMAP after fly scan."""
        yield from self.set_collection_mode("MCA SPECTRA")

    @mode_setter("preset_mode")
    def set_preset_mode(mode):
        """Set preset mode."""
        pass

    @mode_setter("collection_mode")
    def set_collection_mode(mode):
        """Set collection mode."""
        pass

    @mode_setter("status_rate")
    def set_status_rate(rate):
        """Set status update rate."""
        pass

    @mode_setter("read_rate")
    def set_read_rate(rate):
        """Set read rate."""
        pass

    @value_setter("preset_real_time")
    def set_real_time(real_time):
        """Set preset real time."""
        pass

    @value_setter("preset_live_time")
    def set_live_time(live_time):
        """Set preset live time."""
        pass

    @value_setter("pixels_per_run")
    def set_pixels_per_run(numpts):
        """Set number of pixels per run."""
        pass

    @value_setter("stop_all")
    def set_stop_all(stop_all):
        """Set stop all signal."""
        pass

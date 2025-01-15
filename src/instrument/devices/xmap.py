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
from ..devices.utils import mode_setter, value_setter


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

    @mode_setter("collection_mode")
    def set_collection_mode(mode):
        pass

    @value_setter("preset_real_time")
    def set_real_time(real_time):
        pass

    @value_setter("preset_live_time")
    def set_live_time(live_time):
        pass

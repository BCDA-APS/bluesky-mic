from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal
from ..utils.device_utils import value_setter


class SIS3820(Device):
    num_ch_used = Component(EpicsSignal, "NuseAll")
    stop_all = Component(EpicsSignal, "StopAll")
    erase_start = Component(EpicsSignal, "EraseStart")

    def before_flyscan(self, num_pts):
        yield from self.set_stop_all(1)
        yield from self.set_num_ch_used(num_pts)

    @value_setter("num_ch_used")
    def set_num_ch_used(num_ch_used):
        pass

    @value_setter("stop_all")
    def set_stop_all(stop_all):
        pass

from s19.devices.utils import mode_setter
from s19.devices.utils import value_setter
from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal


class KohzuMono(Device):
    energy = Component(EpicsSignal, "BraggEAO")
    energy_rbv = Component(EpicsSignal, "BraggERdbkAO")
    mode = Component(EpicsSignal, "KohzuModeBO")
    mode2 = Component(EpicsSignal, "KohzuMode2MO")
    move = Component(EpicsSignal, "KohzuPutBO")
    moving = Component(EpicsSignal, "KohzuMoving")

    @value_setter("energy")
    def set_energy(energy):
        pass

    @value_setter("move")
    def set_move(move):
        pass

    @mode_setter("mode")
    def set_mode(mode):
        pass

    @mode_setter("mode2")
    def set_mode2(mode2):
        pass

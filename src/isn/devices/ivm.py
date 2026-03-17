from ophyd import Device
from ophyd import Component
from ophyd import EpicsMotor

class Ivm(Device):
    x = Component(EpicsMotor, "m3")
    y = Component(EpicsMotor, "m1")
    z = Component(EpicsMotor, "m2")
    
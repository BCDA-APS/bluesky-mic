from ophyd import Device
from ophyd import Component
from ophyd import EpicsMotor

class Cryo(Device):
    rot_lower = Component(EpicsMotor, "m8")
    rot_upper = Component(EpicsMotor, "m7")
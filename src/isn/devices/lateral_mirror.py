from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor


class Lateral_Mirror(Device):
    jack = Component(EpicsMotor, ":m9")
    lateral = Component(EpicsMotor, ":m11")
    pitch = Component(EpicsMotor, ":m13")
    fine_pitch = Component(EpicsMotor, ":piezo:m2")
    bender_1 = Component(EpicsMotor, ":m15")
    bender_2 = Component(EpicsMotor, ":m16")

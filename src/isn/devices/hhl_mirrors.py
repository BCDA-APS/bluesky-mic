"""HHL mirrors in 19ID-A"""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor


class HHL_Mirrors(Device):
    """HHL mirrors device for 19ID-A."""

    jack = Component(EpicsMotor, ":m1")
    lateral = Component(EpicsMotor, ":m3")
    pitch = Component(EpicsMotor, ":m5")
    fine_pitch = Component(EpicsMotor, ":piezo:m1")
    bender_1 = Component(EpicsMotor, ":m7")
    bender_2 = Component(EpicsMotor, ":m8")

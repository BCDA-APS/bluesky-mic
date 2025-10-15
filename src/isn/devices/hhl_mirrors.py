"""HHL mirrors in 19ID-A"""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor


class HHL_Mirrors(Device):
    """HHL mirrors device for 19ID-A."""

    jack = Component(EpicsMotor, ":m1", labels=("motor", "baseline",))
    lateral = Component(EpicsMotor, ":m3", labels=("motor", "baseline",))
    pitch = Component(EpicsMotor, ":m5", labels=("motor", "baseline",))
    fine_pitch = Component(EpicsMotor, ":piezo:m1", labels=("motor", "baseline",))
    bender_1 = Component(EpicsMotor, ":m7", labels=("motor", "baseline",))
    bender_2 = Component(EpicsMotor, ":m8", labels=("motor", "baseline",))

"""HHL mirrors in 19ID-A"""

from ophyd import Component, PositionerBase
from ophyd import Device
from ophyd import EpicsMotor


class HHL_Mirrors(Device):
    """HHL mirrors device for 19ID-A."""

    jack = Component(EpicsMotor, ":m1", labels=("motor", "baseline",), kind="config")
    lateral = Component(EpicsMotor, ":m3", labels=("motor", "baseline",), kind="config")
    pitch = Component(EpicsMotor, ":m5", labels=("motor", "baseline",), kind="config")
    fine_pitch = Component(EpicsMotor, ":piezo:m1", labels=("motor", "baseline",), kind="config")
    bender_1 = Component(EpicsMotor, ":m7", labels=("motor", "baseline",), kind="config")
    bender_2 = Component(EpicsMotor, ":m8", labels=("motor", "baseline",), kind="config")

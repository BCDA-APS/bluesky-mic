from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor


class Rayspec(Device):
    """HHL mirrors device for 19ID-A."""

    x = Component(EpicsMotor, ":m12", labels=("motor",), kind="config")
    y = Component(EpicsMotor, ":m13", labels=("motor",), kind="config")
    z = Component(EpicsMotor, ":m14", labels=("motor",), kind="config")
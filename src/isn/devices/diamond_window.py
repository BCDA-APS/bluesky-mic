from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor


class Diamond_Window(Device):
    x = Component(EpicsMotor, ":m1", labels=("motors",))
    y = Component(EpicsMotor, ":m2", labels=("motors",))

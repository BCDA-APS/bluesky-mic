from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor


class XRayEye(Device):
    x = Component(EpicsMotor, ":m1", labels=("motor",))

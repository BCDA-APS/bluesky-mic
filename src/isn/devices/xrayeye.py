from ophyd import Component, Device, EpicsMotor


class XRayEye(Device):
    x = Component(EpicsMotor, ':m1', labels=('motor',))
'''X-ray eye stage'''

__all__ = ['xeye']

from ophyd import Component, Device, EpicsMotor


class XRayEye(Device):
    x = Component(EpicsMotor, 'm1', labels=('motor',))


xeye = XRayEye('19idXEYE:', name='xeye')
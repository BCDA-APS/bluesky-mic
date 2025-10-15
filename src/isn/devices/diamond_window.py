from ophyd import Device, Component, EpicsMotor

class Diamond_Window(Device):
    x = Component(EpicsMotor, ':m1', labels=('motor',))
    y = Component(EpicsMotor, ':m2', labels=('motor',))
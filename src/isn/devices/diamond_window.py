from ophyd import Device, Component, EpicsMotor

class Diamond_Window(Device):
    x = Component(EpicsMotor, ':m1', kind='config', labels=('motor','baseline'))
    y = Component(EpicsMotor, ':m2', kind='config', labels=('motor','baseline'))
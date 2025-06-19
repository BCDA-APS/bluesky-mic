from ophyd import Device, Component, EpicsMotor

class Lateral_Mirror(Device):
    jack = Component(EpicsMotor, ':m9', kind='config', labels=('motor',))
    lateral = Component(EpicsMotor, ':m11', kind='config', labels=('motor',))
    pitch = Component(EpicsMotor, ':m13', kind='config', labels=('motor',))
    fine_pitch = Component(EpicsMotor, ':piezo:m2', kind='config', labels=('motor',))
    bender_1 = Component(EpicsMotor, ':m15', kind='config', labels=('motor',))
    bender_2 = Component(EpicsMotor, ':m16', kind='config', labels=('motor',))
'''
Temporary device implementation for sample micronix stages.
Later, we will need to modify the sample to incorporate this.
'''

from ophyd import (
    Device,
    Component,
    EpicsMotor
)

class Micronix(Device):
    theta = Component(EpicsMotor, "m4")
    x = Component(EpicsMotor, "m2")
    z = Component(EpicsMotor, "m3")
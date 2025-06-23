from ophyd import Device, Component, EpicsMotor, EpicsSignal

'''Probably we need to do an Epics picomotor implementation that takes into account the different 
possible motions available with these complex motors.
'''

class KB(Device):
    # th_x = Component(EpicsMotor, ':m9', kind='config', labels=('motor',)) #Need to think right way of implementing it
    th_y = Component(EpicsMotor, ':SM1', kind='config', labels=('motor','baseline')) 
    th_y = Component(EpicsSignal, ':cap5:voltage', kind='config', labels=('baseline'))
    th_z = Component(EpicsMotor, ':SM2', kind='config', labels=('motor','baseline'))
    th_z_cap = Component(EpicsSignal, ':cap6:voltage', kind='config', labels=('baseline'))
    x = Component(EpicsMotor, ':m18', kind='config', labels=('motor',))
    x_cap = Component(EpicsSignal, ':cap4:voltage', kind='config', labels=('baseline'))
    # y = Component(EpicsMotor, ':m9', kind='config', labels=('motor',)) #Need to think how to do it properly
    z = Component(EpicsMotor, ':m17', kind='config', labels=('motor',))
    z_cap = Component(EpicsSignal, ':cap3:voltage', kind='config', labels=('baseline'))
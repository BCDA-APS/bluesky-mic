'''Class that defines and creates the two BDAs in ISN'''


from ophyd import Device, FormattedComponent, EpicsMotor

class BDA(Device):

    def __init__(self, prefix, axis, **kwargs):
        self.axis = axis
        super().__init__(prefix=prefix, **kwargs)

    low_slit = FormattedComponent(EpicsMotor, '{prefix}:Slit1{axis}xn', labels=('motors',), kind = 'config')
    high_slit = FormattedComponent(EpicsMotor, '{prefix}:Slit1{axis}xp', labels=('motors',), kind = 'config')
    size = FormattedComponent(EpicsMotor, '{prefix}:Slit1{axis}size', labels=('motors',), kind = 'config')
    center = FormattedComponent(EpicsMotor, '{prefix}:Slit1{axis}center', labels=('motors',), kind = 'config')


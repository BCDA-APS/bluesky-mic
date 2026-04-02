from ophyd import Component, Device, EpicsSignal, EpicsSignalRO, PVPositioner


class BDA_Stepper_X(PVPositioner):
    done = Component(EpicsSignalRO, ':Xy:RunPrg')
    stop_signal = Component(EpicsSignal, ':Xy:Abort')
    setpoint = Component(EpicsSignal, ':UX:RqsPos')
    readback = Component(EpicsSignalRO, ':UX:ActPos')

class BDA_Stepper_Y(PVPositioner):
    done = Component(EpicsSignalRO, ':Xy:RunPrg')
    stop_signal = Component(EpicsSignal, ':Xy:Abort')
    setpoint = Component(EpicsSignal, ':UY:RqsPos')
    readback = Component(EpicsSignalRO, ':UY:ActPos')


class BDA(Device):
    """BDA device"""
    x = Component(BDA_Stepper_X, '', kind='config', labels=('motor', ))
    y = Component(BDA_Stepper_Y, '', kind='config', labels=('motor', ))
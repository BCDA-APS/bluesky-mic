from ophyd import Device, Component, EpicsSignal, PVPositioner, EpicsSignalRO
# from ophyd.utils.epics_pvs import raise_if_disconnected

class DeltaTauPiezoX(PVPositioner):
    done = Component(EpicsSignalRO, 'Ps:RunPrg')
    stop_signal = Component(EpicsSignal, 'Ps:Abort')
    setpoint = Component(EpicsSignal, 'PX:RqsPos')
    readback = Component(EpicsSignalRO, 'PX:ActPos')

class DeltaTauStepperX(PVPositioner):
    done = Component(EpicsSignalRO, 'Ps:RunPrg')
    stop_signal = Component(EpicsSignal, 'Ps:Abort')
    setpoint = Component(EpicsSignal, 'SX:RqsPos')
    readback = Component(EpicsSignalRO, 'SX:ActPos')

class CombinationMotor(Device):
    stepper = Component(DeltaTauStepperX, '', kind='config', labels=('motor', ))
    piezo = Component(DeltaTauPiezoX, '', kind='config', labels=('motor', ))


class Sample(Device):
    x = Component(CombinationMotor, ':SM:', kind='config', labels=('motor', ))
    # y = Component(DeltaTauMotor, ':SY:PY', kind='config', labels=('motor', ))
    # z = Component(DeltaTauMotor, ':SM:SZ', kind='config', labels=('motor', ))
    # tomo_rot = Component(DeltaTauMotor, ':SM:CT', kind='config', labels=('motor', ))
    # sm_rot = Component(DeltaTauMotor, ':SM:ST', kind='config', labels=('motor', ))

    
    
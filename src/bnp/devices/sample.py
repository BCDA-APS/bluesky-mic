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

class DeltaTauPiezoY(PVPositioner):
    done = Component(EpicsSignalRO, 'Ps:RunPrg')
    stop_signal = Component(EpicsSignal, 'Ps:Abort')
    setpoint = Component(EpicsSignal, 'PY:RqsPos')
    readback = Component(EpicsSignalRO, 'PY:ActPos')

class DeltaTauStepperY(PVPositioner):
    done = Component(EpicsSignalRO, 'Ps:RunPrg')
    stop_signal = Component(EpicsSignal, 'Ps:Abort')
    setpoint = Component(EpicsSignal, 'SY:RqsPos')
    readback = Component(EpicsSignalRO, 'SY:ActPos')

class DeltaTauStepperZ(PVPositioner):
    done = Component(EpicsSignalRO, 'Ps:RunPrg')
    stop_signal = Component(EpicsSignal, 'Ps:Abort')
    setpoint = Component(EpicsSignal, 'SZ:RqsPos')
    readback = Component(EpicsSignalRO, 'SZ:ActPos')

class DeltaTauStepperTheta(PVPositioner):
    done = Component(EpicsSignalRO, 'Ps:RunPrg')
    stop_signal = Component(EpicsSignal, 'Ps:Abort')
    setpoint = Component(EpicsSignal, 'ST:RqsPos')
    readback = Component(EpicsSignalRO, 'ST:ActPos')

class DeltaTauStepperTomo(PVPositioner):
    done = Component(EpicsSignalRO, 'Ps:RunPrg')
    stop_signal = Component(EpicsSignal, 'Ps:Abort')
    setpoint = Component(EpicsSignal, 'CT:RqsPos')
    readback = Component(EpicsSignalRO, 'CT:ActPos')

class CombinationMotorX(Device):
    stepper = Component(DeltaTauStepperX, '', kind='config', labels=('motor', ))
    piezo = Component(DeltaTauPiezoX, '', kind='config', labels=('motor', ))
    motion = Component(EpicsSignal, 'Ps:Motion', kind='config', labels=('motor', ))

class CombinationMotorY(Device):
    stepper = Component(DeltaTauStepperY, '', kind='config', labels=('motor', ))
    piezo = Component(DeltaTauPiezoY, '', kind='config', labels=('motor', ))
    motion = Component(EpicsSignal, 'Ps:Motion', kind='config', labels=('motor', ))

class Sample(Device):
    x = Component(CombinationMotorX, ':SM:', kind='config', labels=('motor', ))
    y = Component(CombinationMotorY, ':SY:', kind='config', labels=('motor', ))
    z = Component(DeltaTauStepperZ, ':SM:', kind='config', labels=('motor', ))
    theta = Component(DeltaTauStepperTheta, ':SM:', kind='config', labels=('motor', ))
    tomo = Component(DeltaTauStepperTomo, ':SM:', kind='config', labels=('motor', ))
    busy = Component(EpicsSignal, ':SM:Ps:Busy', kind='config', labels=('signal', ))
    
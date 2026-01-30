from bnp.devices.deltaTau import DeltaTauPiezoBase
from ophyd import Component, Device, EpicsSignal, EpicsSignalRO, PVPositioner

class DeltaTauPiezoX(DeltaTauPiezoBase):
    done = Component(EpicsSignalRO, 'Ps:RunPrg')
    stop_signal = Component(EpicsSignal, 'Ps:Abort')
    setpoint = Component(EpicsSignal, 'PX:RqsPos')
    readback = Component(EpicsSignalRO, 'PX:ActPos')
    center = Component(EpicsSignal, 'Ps:xCenter.PROC')


class DeltaTauStepperX(PVPositioner):
    done = Component(EpicsSignalRO, 'Ps:RunPrg')
    stop_signal = Component(EpicsSignal, 'Ps:Abort')
    setpoint = Component(EpicsSignal, 'SX:RqsPos')
    readback = Component(EpicsSignalRO, 'SX:ActPos')

class DeltaTauPiezoY(DeltaTauPiezoBase):
    done = Component(EpicsSignalRO, 'Ps:RunPrg')
    stop_signal = Component(EpicsSignal, 'Ps:Abort')
    setpoint = Component(EpicsSignal, 'PY:RqsPos')
    readback = Component(EpicsSignalRO, 'PY:ActPos')
    center = Component(EpicsSignal, 'Ps:yCenter.PROC')

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
    
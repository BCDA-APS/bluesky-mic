from bnp.devices.deltaTau import DeltaTauPiezoBase
from bnp.devices.deltaTau import DeltaTauPVPositionerBase
from ophyd import Component, Device, EpicsSignal, EpicsSignalRO


class SampleCoorOffset(Device):
    x_sample_origin = Component(EpicsSignalRO, ':SM:SXO.VAL', kind='config', labels=('signal',))
    y_sample_origin = Component(EpicsSignalRO, ':SY:SYO.VAL', kind='config', labels=('signal',))
    z_sample_origin = Component(EpicsSignalRO, ':SM:SZO.VAL', kind='config', labels=('signal',))
    x_optical_axis = Component(EpicsSignalRO, ':SM:SXA.VAL', kind='config', labels=('signal',))
    y_optical_axis = Component(EpicsSignalRO, ':SY:SYA.VAL', kind='config', labels=('signal',))
    z_optical_axis = Component(EpicsSignalRO, ':SM:SZA.VAL', kind='config', labels=('signal',))

class DeltaTauPiezoX(DeltaTauPiezoBase):
    done = Component(EpicsSignalRO, 'Ps:RunPrg')
    stop_signal = Component(EpicsSignal, 'Ps:Abort')
    setpoint = Component(EpicsSignal, 'PX:RqsPos')
    readback = Component(EpicsSignalRO, 'PX:ActPos')
    center = Component(EpicsSignal, 'Ps:xCenter.PROC')
    state = Component(EpicsSignal, 'PX:NgLimSet')

class DeltaTauStepperX(DeltaTauPVPositionerBase):
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
    state = Component(EpicsSignal, 'PY:NgLimSet')

class DeltaTauStepperY(DeltaTauPVPositionerBase):
    done = Component(EpicsSignalRO, 'Ps:RunPrg')
    stop_signal = Component(EpicsSignal, 'Ps:Abort')
    setpoint = Component(EpicsSignal, 'SY:RqsPos')
    readback = Component(EpicsSignalRO, 'SY:ActPos')

class DeltaTauStepperZ(DeltaTauPVPositionerBase):
    done = Component(EpicsSignalRO, 'Ps:RunPrg')
    stop_signal = Component(EpicsSignal, 'Ps:Abort')
    setpoint = Component(EpicsSignal, 'SZ:RqsPos')
    readback = Component(EpicsSignalRO, 'SZ:ActPos')

class DeltaTauStepperTheta(DeltaTauPVPositionerBase):
    done = Component(EpicsSignalRO, 'Ps:RunPrg')
    stop_signal = Component(EpicsSignal, 'Ps:Abort')
    setpoint = Component(EpicsSignal, 'ST:RqsPos')
    readback = Component(EpicsSignalRO, 'ST:ActPos')

class DeltaTauStepperTomo(DeltaTauPVPositionerBase):
    done = Component(EpicsSignalRO, 'Ps:RunPrg')
    stop_signal = Component(EpicsSignal, 'Ps:Abort')
    setpoint = Component(EpicsSignal, 'CT:RqsPos')
    readback = Component(EpicsSignalRO, 'CT:ActPos')

class CombinationMotorX(Device):
    stepper = Component(DeltaTauStepperX, '', kind='config', labels=('motor', ))
    piezo = Component(DeltaTauPiezoX, '', kind='config', labels=('motor', ))
    motion = Component(EpicsSignal, 'Ps:Motion', kind='config', labels=('motor', ))

    def set_re_stop_suppressed(self, suppressed: bool = True):
        self.stepper.set_re_stop_suppressed(suppressed)
        self.piezo.set_re_stop_suppressed(suppressed)

class CombinationMotorY(Device):
    stepper = Component(DeltaTauStepperY, ':SY:', kind='config', labels=('motor', ))
    piezo = Component(DeltaTauPiezoY, ':SY:', kind='config', labels=('motor', ))
    motion = Component(EpicsSignal, ':SY:Ps:Motion', kind='config', labels=('motor', ))
    piezo_value = Component(EpicsSignalRO, ':M7010.VAL', kind='config', labels=('motor', ))
    piezo_max_value = 31000

    def set_re_stop_suppressed(self, suppressed: bool = True):
        self.stepper.set_re_stop_suppressed(suppressed)
        self.piezo.set_re_stop_suppressed(suppressed)

class Sample(Device):
    x = Component(CombinationMotorX, ':SM:', kind='config', labels=('motor', ))
    y = Component(CombinationMotorY, '', kind='config', labels=('motor', ))
    z = Component(DeltaTauStepperZ, ':SM:', kind='config', labels=('motor', ))
    theta = Component(DeltaTauStepperTheta, ':SM:', kind='config', labels=('motor', ))
    tomo = Component(DeltaTauStepperTomo, ':SM:', kind='config', labels=('motor', ))
    busy = Component(EpicsSignal, ':SM:Ps:Busy', kind='config', labels=('signal', ))

    def set_re_stop_suppressed(self, suppressed: bool = True):
        self.x.set_re_stop_suppressed(suppressed)
        self.y.set_re_stop_suppressed(suppressed)
        self.z.set_re_stop_suppressed(suppressed)
        self.theta.set_re_stop_suppressed(suppressed)
        self.tomo.set_re_stop_suppressed(suppressed)

from ophyd import Device, Component, EpicsMotor, EpicsSignal

from bluesky.plan_stubs import mv


class EpicsMotorExtension(EpicsMotor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    tweak_value = Component(EpicsSignal, ".TWV", kind='config')
    tweak_forward = Component(EpicsSignal, ".TWF")
    tweak_reverse = Component(EpicsSignal, ".TWR")


class Sample(Device):

    x = Component(EpicsMotorExtension, ":m2", kind='config', labels=('motor', ))
    y = Component(EpicsMotor, ":m3", kind='config', labels=('motor', ))
    z = Component(EpicsMotor, ":m1", kind='config', labels=('motor', ))

    all_piezos = Component(EpicsMotor, ":SM1", kind='config', labels=('motor', ))

    analog_on = Component(EpicsSignal, ":userStringSeq2.PROC")
    analog_off = Component(EpicsSignal, ":userStringSeq1.PROC")

    def enable_analog_control(self):
        self.analog_on.put("1", wait=True)

    def disable_analog_control(self):
        self.analog_off.put("1", wait=True)
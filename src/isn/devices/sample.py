from ophyd import Device, Component, EpicsMotor, EpicsSignal

from bluesky.plan_stubs import mv


class EpicsMotorWithTweak(EpicsMotor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    tweak_value = Component(EpicsSignal, ".TWV")
    tweak_forward = Component(EpicsSignal, ".TWF", kind='config')
    tweak_reverse = Component(EpicsSignal, ".TWR", kind='config')


class Sample(Device):

    # x = Component(EpicsMotor, ":m2", kind='config', labels=('motor', ))
    # y = Component(EpicsMotor, ":m3", kind='config', labels=('motor', ))
    # z = Component(EpicsMotor, ":m1", kind='config', labels=('motor', ))

    # all_piezos = Component(EpicsMotor, ":SM1", kind='config', labels=('motor', ))

    x = Component(EpicsMotorWithTweak, ":m2")
    y = Component(EpicsMotor, ":m3")
    z = Component(EpicsMotor, ":m1")

    fine_y = Component(EpicsMotor, ":SM1")

    analog_on = Component(EpicsSignal, ":userStringSeq2.PROC")
    analog_off = Component(EpicsSignal, ":userStringSeq1.PROC")

    def enable_analog_control(self):
        self.analog_on.put("1", wait=True)

    def disable_analog_control(self):
        self.analog_off.put("1", wait=True)
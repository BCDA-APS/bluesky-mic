from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO

from time import sleep

from apstools.devices.motor_mixins import EpicsMotorServoMixin

class ServoMotor(EpicsMotorServoMixin, EpicsMotor):

    @property
    def enabled(self):
        return self.servo.get() in ("Enable")
    
    def enable(self):
        self.servo.put("Enable")

    def disable(self):
        self.servo.put("Disable")


class EpicsMotorWithTweak(EpicsMotor):

    tweak_value = Component(EpicsSignal, ".TWV")
    tweak_forward = Component(EpicsSignal, ".TWF", kind="config")
    tweak_reverse = Component(EpicsSignal, ".TWR", kind="config")


class Sample(Device):

    x = Component(EpicsMotorWithTweak, ":m2")
    y = Component(ServoMotor, ":m3")
    z = Component(EpicsMotor, ":m1")

    fine_y = Component(EpicsMotor, ":SM1")

    analog_on = Component(EpicsSignal, ":userStringSeq2.PROC")
    analog_off = Component(EpicsSignal, ":userStringSeq1.PROC")
    query = Component(EpicsSignal, ":userStringSeq3.PROC")
    query_output = Component(EpicsSignalRO, ":pi:c0:asyn.TINP")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    @property
    def in_analog_mode(self):
        strings = []
        self.query.put(1)
        sleep(0.1)
        for i in range(3):
            strings.append(self.query_output.get())
            if i == 2:
                continue
            sleep(2)

        vals = [int(i[-1]) for i in strings]
        return vals == [4, 4, 4] #4 is analog control, 0 is digital


    def enable_analog_control(self):
        self.analog_on.put("1", wait=True)
        sleep(4.1)

    def disable_analog_control(self):
        self.analog_off.put("1", wait=True)
        sleep(4.1)


from ophyd import Component
from ophyd import FormattedComponent
from ophyd import Device
from ophyd import EpicsMotor
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO

import numpy as np

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

    x = FormattedComponent(EpicsMotorWithTweak, "{aero_prefix}"+"m2")
    y = FormattedComponent(ServoMotor, "{aero_prefix}"+"m3")
    z = FormattedComponent(EpicsMotorWithTweak, "{aero_prefix}"+"m1")

    fine_y = FormattedComponent(EpicsMotor, "{aero_prefix}"+"SM1")

    analog_on = FormattedComponent(EpicsSignal, "{aero_prefix}"+"userStringSeq2.PROC")
    analog_off = FormattedComponent(EpicsSignal, "{aero_prefix}"+"userStringSeq1.PROC")
    query = FormattedComponent(EpicsSignal, "{aero_prefix}"+"userStringSeq3.PROC")
    query_output = FormattedComponent(EpicsSignalRO, "{aero_prefix}"+"pi:c0:asyn.TINP")

    theta = FormattedComponent(EpicsMotor, "{micronix_prefix}"+"m4") #TODO: We need to create an offsetable component that we can use to calibrate sample to sample the real theta position.
    mic_x = FormattedComponent(EpicsMotor, "{micronix_prefix}"+"m2")
    mic_z = FormattedComponent(EpicsMotor, "{micronix_prefix}"+"m3")

    def __init__(self, aero_prefix, micronix_prefix, *args, **kwargs):
        self.aero_prefix = aero_prefix
        self.micronix_prefix = micronix_prefix
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

    def compensating_z(self, x_step):
        '''Returns the amount the z stage would need to compensate for an x_step to keep the sample in focus.'''
        th = self.theta.user_readback.get()
        return x_step*np.tan(-np.radians(th))


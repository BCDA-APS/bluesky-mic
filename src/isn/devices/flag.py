from ophyd.areadetector import DetectorBase
from ophyd.areadetector import ADComponent
from ophyd import FormattedComponent
from ophyd import Component
from ophyd import EpicsMotor

from ophyd.areadetector import CamBase

from bluesky.plan_stubs import mv

class Flag(DetectorBase):

    _default_configuration_attrs = ()

    cam = FormattedComponent(CamBase, "{cam_prefix}")
    motor = FormattedComponent(EpicsMotor, "{motor_prefix}")


    def __init__(self, cam_prefix, motor_prefix, in_position, out_position, *args, **kwargs):
        self.cam_prefix = cam_prefix
        self.motor_prefix = motor_prefix
        self._in_position = in_position
        self._out_position = out_position

        super().__init__(*args, **kwargs)


    def on(self):
        self.cam.acquire.set(1)

    def off(self):
        self.cam.acquire.set(0)

    def move_in(self):
        yield from mv(self.motor, self._in_position)

    def move_out(self):
        yield from mv(self.motor, self._out_position)

    def set_in_position(self, new_in_position=None):
        if not new_in_position:
            new_in_position = self.motor.user_readback.get()

        self._in_position = new_in_position
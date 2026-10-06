"""Optics devices shared by the 2IDD instrument packages."""

import bluesky.plan_stubs as bps
from ophyd import Component, EpicsSignal, EpicsSignalRO

from mic_common.devices.deltaTau import DeltaTauPiezoBase
from mic_common.utils.device_utils import value_setter


class Mono2ID(DeltaTauPiezoBase):
    """Kohzu monochromator used by the 2IDD beamlines."""

    user_setpoint = Component(EpicsSignal, "BraggEAO.VAL")
    user_readback = Component(EpicsSignalRO, "BraggERdbkAO")
    setpoint = Component(EpicsSignal, "BraggEAO.VAL")
    readback = Component(EpicsSignalRO, "BraggERdbkAO")
    mode = Component(EpicsSignal, "KohzuModeBO")
    done = Component(EpicsSignalRO, "KohzuMoving")
    speed_control = Component(EpicsSignal, "KohzuSpeedCtrl")

    POLL_DT = 0.3
    tolerance = 0.0001

    def _is_done(self):
        return abs(self.setpoint.get() - self.readback.get()) <= self.tolerance

    def enable_speed_control(self):
        yield from bps.mv(self.speed_control, 1)

    def disable_speed_control(self):
        yield from bps.mv(self.speed_control, 0)

    def set_auto_mode(self):
        yield from bps.mv(self.mode, 1)

    def set_manual_mode(self):
        yield from bps.mv(self.mode, 0)

    @value_setter("mode")
    def set_mode(mode: str) -> None:
        pass

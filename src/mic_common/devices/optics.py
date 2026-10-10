"""Optics devices shared by the 2IDD instrument packages."""

import logging
import threading
import time

import bluesky.plan_stubs as bps
from ophyd import Component, EpicsSignal, EpicsSignalRO
from ophyd.status import Status

from mic_common.devices.deltaTau import DeltaTauPiezoBase
from mic_common.utils.device_utils import value_setter

logger = logging.getLogger(__name__)


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
    tolerance = 0.0002

    def move(self, position, **kwargs):
        """Move using KohzuMoving semantics: 0=done, 1=busy."""
        status = Status(self)
        thread = threading.Thread(
            target=self._move_with_retry,
            args=(position, status),
            daemon=True,
        )
        thread.start()
        return status

    def _move_with_retry(self, position, status):
        start = time.monotonic()
        self.setpoint.put(position)
        logger.info("%s: moving to %s", self.name, position)

        while time.monotonic() - start < self.TOTAL_TIMEOUT:
            # Readback tolerance is authoritative for this motor. Check it
            # before using KohzuMoving to decide whether to reissue the move.
            if self._is_done():
                status.set_finished()
                return

            # KohzuMoving is 0 when done/not moving and 1 while busy. If the
            # motor stopped outside tolerance, reissue the requested position.
            if self.done.get() == 0:
                self.setpoint.put(position)

            deadline = time.monotonic() + self.RETRY_INTERVAL
            while time.monotonic() < deadline:
                time.sleep(self.POLL_DT)
                if status.done:
                    return
                if self._is_done():
                    status.set_finished()
                    return

        status.set_exception(
            TimeoutError(
                f"{self.name}: move to {position} did not complete within "
                f"{self.TOTAL_TIMEOUT} s"
            )
        )

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

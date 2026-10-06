"""Shared Delta-Tau positioner base classes."""

import logging
import threading
import time

from ophyd import PVPositioner
from ophyd.status import Status

logger = logging.getLogger(__name__)


class DeltaTauPVPositionerBase(PVPositioner):
    """Delta-Tau positioner with optional RunEngine stop suppression."""

    suppress_re_stop = False

    def set_re_stop_suppressed(self, suppressed: bool = True):
        self.suppress_re_stop = bool(suppressed)

    def stop(self, *, success=False):
        if self.suppress_re_stop and success:
            logger.warning(
                "Suppressing RE stop for %s success=%s stop_signal=%s",
                self.name,
                success,
                getattr(getattr(self, "stop_signal", None), "pvname", None),
            )
            return
        return super().stop(success=success)


class DeltaTauRetryPositionerBase(DeltaTauPVPositionerBase):
    """Delta-Tau positioner that retries its command until readback settles."""

    RETRY_INTERVAL = 1.0
    TOTAL_TIMEOUT = 60.0
    POLL_DT = 0.1
    tolerance = 0.01
    settle_time = 0.2

    def move(self, position, **kwargs):
        status = Status(self)
        thread = threading.Thread(
            target=self._move_with_retry,
            args=(position, status),
            daemon=True,
        )
        thread.start()
        return status

    def _is_done(self):
        if abs(self.setpoint.get() - self.readback.get()) <= self.tolerance:
            time.sleep(self.settle_time)
            return True
        return False

    def _move_with_retry(self, position, status):
        start = time.monotonic()
        self.setpoint.put(position)
        logger.info("%s: moving to %s", self.name, position)
        while time.monotonic() - start < self.TOTAL_TIMEOUT:
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


class DeltaTauPiezoBase(DeltaTauRetryPositionerBase):
    """Compatibility name for Delta-Tau piezo axes."""

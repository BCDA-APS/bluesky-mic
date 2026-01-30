import time
import threading

from ophyd import PVPositioner
from ophyd.status import Status
import logging

logger = logging.getLogger(__name__)


class DeltaTauPiezoBase(PVPositioner):
    """
    Base for Delta Tau piezo axes with custom move: re-command the move every
    1 second until setpoint and readback agree within tolerance (handles
    controllers that need repeated triggers). "Done" is determined by
    setpoint vs readback, not the hardware done signal.
    """
    # Subclasses define: done, stop_signal, setpoint, readback

    RETRY_INTERVAL = 1.0   # seconds to wait before re-commanding move
    TOTAL_TIMEOUT = 60.0   # max seconds before giving up
    POLL_DT = 0.02         # seconds between done checks
    tolerance = 0.01       # |setpoint - readback| must be <= this to be "done"

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
        """Consider move done when setpoint and readback agree within tolerance."""
        return abs(self.setpoint.get() - self.readback.get()) <= self.tolerance

    def _move_with_retry(self, position, status):
        start = time.monotonic()
        while time.monotonic() - start < self.TOTAL_TIMEOUT:
            if self.done.get() == 0:
                self.setpoint.put(position)
                logger.info(f"{self.name}: moving to {position}")
            else:
                logger.warning(f"{self.name}: busy, skipping move to {position}")
            deadline = time.monotonic() + self.RETRY_INTERVAL
            while time.monotonic() < deadline:
                if status.done:
                    # RunEngine set status via set_exception(RequestAbort) on abort
                    return
                if self._is_done():
                    status.set_finished()
                    return
                time.sleep(self.POLL_DT)
            # 1 sec elapsed and not done — re-command and loop
        status.set_exception(TimeoutError(
            f"{self.name}: move to {position} did not complete within "
            f"{self.TOTAL_TIMEOUT} s"
        ))
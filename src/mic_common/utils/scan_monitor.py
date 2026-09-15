"""
Creating a list of scan monitoring function so that Bluesky Plans can subscribe to it

@author: yluo(grace227)

List of functions::

    # # watch_counter( ... ): # Monitor and log the counter value

"""

import logging
import time

import bluesky.plan_stubs as bps
from ophyd.status import Status

logger = logging.getLogger(__name__)

SCANNUM_DIGITS = 4


class ScanMonitor:
    """Monitor and log scan progress.

    Attributes:
        current_line (int): Current line being scanned.
        line_time_in (float): Time when line scan started.
        line_time_out (float): Time when line scan ended.
        line_delta (float): Time taken for line scan.
        scan_time_remaining (float): Estimated remaining scan time.
        outter_print_msg (bool): Whether to print outer loop messages.
        sample (Sample, optional): Sample ophyd device.
    """

    current_line = 0
    line_time_in = 0
    line_time_out = 0
    line_delta = 0
    scan_time_remaining = 0
    outter_print_msg = False
    sample = None
    verbose = False
    pause_sent = False
    
    def __init__(
        self,
        numpts_x=None,
        scan_name=None,
        numpts_y=0,
        sample=None,
        verbose=False,
        execute_signal=None,
        pause_signal=None,
        abort_signal=None,
        recover_y_piezo=False,
        name="scan_monitor",
    ):
        """Initialize ScanMonitor.

        Parameters:
            numpts_x (int, optional): Number of points in X direction.
            scan_name (str, optional): Name of the scan.
            numpts_y (int, optional): Number of points in Y direction.
        """
        self.scan_active = False
        self.counter_active = False
        self.st = Status()
        self.numpts_x = numpts_x
        self.numpts_y = numpts_y
        self.scan_name = scan_name
        self.sample = sample
        self.verbose = verbose
        self._execute_signal = execute_signal
        self._pause_signal = pause_signal
        self._abort_signal = abort_signal
        self._recover_y_piezo = bool(recover_y_piezo)
        self.name = name
        self.execute_done = False
        self.outer_idle = False
        self.has_outer_loop = False
        self.inner_scan_active = False
        self.y_piezo_recovered_for_inner_scan = False

    def pause(self):
        if self._pause_signal is not None and not self.pause_sent:
            logger.info(
                "Pausing scan monitor %s via %s",
                self.name,
                getattr(self._pause_signal, "pvname", self._pause_signal),
            )
            self._pause_signal.put(1)
            self.pause_sent = True
            time.sleep(0.5)

    def resume(self):
        if self._pause_signal is not None and self.pause_sent:
            logger.info(
                "Resuming scan monitor %s via %s",
                self.name,
                getattr(self._pause_signal, "pvname", self._pause_signal),
            )
            self._pause_signal.put(0)
            self.pause_sent = False
            time.sleep(0.5)

    def stop(self, success=False):
        self.scan_active = False
        self.counter_active = False
        self.execute_done = False
        self.outer_idle = False
        if self._abort_signal is not None:
            self._abort_signal.put(1)
            time.sleep(0.5)
            self._abort_signal.put(1)
            time.sleep(0.5)

    def trigger(self):
        """Start the underlying scan and return a Status that finishes when scan ends."""
        if self._execute_signal is None:
            raise RuntimeError("ScanMonitor.trigger() requires an execute_signal.")

        if self.scan_active and self.st is not None and not self.st.done:
            return self.st

        self.st = Status()
        self.scan_active = True
        self.counter_active = True
        self.line_time_in = time.perf_counter()
        self.current_line = 0
        self.execute_done = False
        self.outer_idle = False
        self.inner_scan_active = False
        self.y_piezo_recovered_for_inner_scan = False

        self._execute_signal.put(1)
        return self.st

    def _finish_if_ready(self):
        # 1D scans have no outer loop, so nothing ever sets ``outer_idle``;
        # only gate on it when an outer loop is actually being monitored.
        outer_ok = self.outer_idle or not self.has_outer_loop
        if self.scan_active and self.execute_done and outer_ok:
            self.scan_active = False
            self.counter_active = False
            self.st.set_finished()
            logger.info(f"FINISHED: ScanMonitor.st {self.st}")

    def update_eta(self):
        """Update estimated time remaining."""
        self.line_time_out = time.perf_counter()
        self.line_delta = round(self.line_time_out - self.line_time_in, 2)
        self.line_time_in = self.line_time_out

    def watch_counter_outter(self, old_value, value, **kwargs):
        """Monitor outer loop counter.

        Parameters:
            old_value (int): Previous counter value.
            value (int): Current counter value.
            **kwargs: Additional keyword arguments.
        """

        if self.counter_active:
            if value >= 1:
                self.update_eta()
                self.scan_time_remaining = round((self.numpts_y - value) * self.line_delta, 2)
                self.current_line = value
                if self.outter_print_msg:
                    prog = round(100 * value / self.numpts_y, 2)
                    msg = f"Filename: {self.scan_name}, Scan_progress: {prog}%, "
                    msg += (
                        f"Scanned : {value}/{self.numpts_y}, "
                        f"Scan_remaining : {self.scan_time_remaining}, "
                    )
                    msg += f"Line_eta : {self.line_delta}"
                    logger.info(msg)

    def watch_counter_inner(self, old_value, value, **kwargs):
        """Monitor inner loop counter.

        Parameters:
            old_value (int): Previous counter value.
            value (int): Current counter value.
            **kwargs: Additional keyword arguments.
        """
        if self.counter_active and self.numpts_x is not None:
            if all([value > 0, value > old_value, value < self.numpts_x]):
                if self.numpts_y == 0:
                    self.update_eta()
                    self.scan_time_remaining = round((self.numpts_x - value) * self.line_delta, 2)
                    prog = round(100 * value / self.numpts_x, 2)
                    msg = f"Filename: {self.scan_name}, Scan_progress: {prog}%, "
                    msg += f"Line: 1/1, Scan_remaining: {self.scan_time_remaining}, "
                    msg += f"Scanned {value}/{self.numpts_x}"
                    logger.info(msg)
                else:
                    prog = round(
                        100
                        * (self.numpts_x * self.current_line + value)
                        / (self.numpts_x * self.numpts_y),
                        2,
                    )
                    msg = f"Filename: {self.scan_name}, Scan_progress: {prog}%, "
                    msg += (
                        f"Line: {self.current_line}/{self.numpts_y}, "
                        f"Scan_remaining: {self.scan_time_remaining}, "
                        f"Line_eta: {self.line_delta}, "
                        f"Scanned: {value}/{self.numpts_x}"
                    )
                    logger.info(msg)

    def watch_execute_scan(self, old_value, value, **kwargs):
        """Monitor scan execution.

        Parameters:
            old_value (int): Previous execution value.
            value (int): Current execution value.
            **kwargs: Additional keyword arguments.
        """
        if self.scan_active and self._value_matches(old_value, 1) and self._value_matches(value, 0):
            self.execute_done = True
            self._finish_if_ready()

    def watch_inner_execute_scan(self, old_value, value, **kwargs):
        """Center sample y piezo after an inner 1D scan finishes, if needed."""
        if not self.scan_active:
            return

        if self._value_matches(value, 1):
            self.inner_scan_active = True
            self.y_piezo_recovered_for_inner_scan = False
        elif self._value_matches(old_value, 1) and self._value_matches(value, 0):
            self.inner_scan_active = False
            self.recover_y_piezo_if_needed(reason="inner execute_scan finished")

    def watch_faze_outer(self, old_value, value, **kwargs):
        """Monitor outer scan phase and mark completion once it returns to IDLE."""
        if self.scan_active:
            self.outer_idle = self._scan_phase_is_idle(value)
            self._finish_if_ready()

    def watch_faze_inner(self, old_value, value, **kwargs):
        """Monitor inner loop counter.

        Parameters:
            old_value (int): Previous counter value.
            value (int): Current counter value.
            **kwargs: Additional keyword arguments.
        """
        if self.verbose:
            logger.debug(f"inner faze: old_value: {old_value}, value: {value}")

        if self.sample is not None:
            if self.counter_active:
                if not self._scan_phase_is_idle(value):
                    self.inner_scan_active = True
                    self.y_piezo_recovered_for_inner_scan = False
                elif self.inner_scan_active:
                    self.inner_scan_active = False
                    self.recover_y_piezo_if_needed(reason="inner scan phase idle")

                adjust_sample_x_speed = self._can_adjust_sample_x_speed()
                if self._value_matches(value, 7) and adjust_sample_x_speed:
                    if self.sample.x.velocity.get() != self.sample.x.scan_speed:
                        self.sample.x.set_speed(self.sample.x.scan_speed)
                        if self.verbose:
                            logger.debug(f"set samx speed to {self.sample.x.scan_speed}")
                        time.sleep(0.2)
                elif self._value_matches(value, 5) and hasattr(self.sample.x, "motor_is_moving"):
                    if self.verbose:
                        logger.debug(f"is samx moving: {self.sample.x.motor_is_moving.get()}")
                elif adjust_sample_x_speed:
                    if self.sample.x.velocity.get() != self.sample.x.max_velocity.get():
                        self.sample.x.set_speed(self.sample.x.max_velocity.get())
                        if self.verbose:
                            logger.debug(f"set samx speed to {self.sample.x.max_velocity.get()}")
                        time.sleep(0.2)

    def _can_adjust_sample_x_speed(self):
        if self.sample is None or not hasattr(self.sample, "x"):
            return False
        return all(
            hasattr(self.sample.x, attr)
            for attr in ("velocity", "scan_speed", "max_velocity", "set_speed")
        )

    @staticmethod
    def _value_matches(value, target):
        try:
            return float(value) == float(target)
        except Exception:
            return str(value).strip().lower() == str(target).strip().lower()

    def _scan_phase_is_idle(self, value):
        if self._value_matches(value, 0):
            return True
        return str(value).strip().lower() in {"idle", "done"}

    def recover_y_piezo_if_needed(self, reason="inner scan finished"):
        """Center the sample y piezo once per inner scan when the piezo is over limit."""
        if not self._recover_y_piezo or self.sample is None:
            return
        if self.y_piezo_recovered_for_inner_scan:
            return

        try:
            piezo_value = abs(float(self.sample.y.piezo_value.get()))
            piezo_max_value = float(self.sample.y.piezo_max_value)
            logger.info(
                "sample.y piezo recovery check after %s: absolute y_piezo_value=%s, y_piezo_max=%s",
                reason,
                piezo_value,
                piezo_max_value,
            )
        except Exception as exc:
            logger.warning(f"Could not check sample.y piezo recovery limit: {exc}")
            self.y_piezo_recovered_for_inner_scan = True
            return

        if piezo_value <= piezo_max_value:
            self.y_piezo_recovered_for_inner_scan = True
            return

        try:
            logger.warning(
                "Centering sample.y.piezo after %s; y_piezo_value=%s exceeds y_piezo_max=%s",
                reason,
                piezo_value,
                piezo_max_value,
            )
            self.sample.y.piezo.center.put(1)
        except Exception:
            logger.exception("Failed to center sample.y.piezo after %s", reason)
        finally:
            self.y_piezo_recovered_for_inner_scan = True

# Usage
def execute_scan_1d(scan1, scan_name="", abort_signal=None, verbose=False):
    """Execute a 1D scan with monitoring.

    Parameters:
        scan1: Scan object.
        scan_name (str): Name of the scan.
    """
    watcher = ScanMonitor(
        numpts_x=scan1.number_points.value,
        scan_name=scan_name.zfill(SCANNUM_DIGITS),
        execute_signal=scan1.execute_scan,
        pause_signal=scan1.wait,
        abort_signal=abort_signal,
        name=f"{scan1.name}_monitor",
    )

    logger.info("Done setting up scan, about to start scan")
    logger.info("Start executing scan")

    scan1.execute_scan.subscribe(watcher.watch_execute_scan)  # Subscribe to the scan
    scan1.current_point.subscribe(watcher.watch_counter_inner)

    try:
        yield from bps.trigger(watcher, wait=True)
    except BaseException:
        watcher.stop(success=False)
        raise
    finally:
        scan1.current_point.unsubscribe_all()
        scan1.execute_scan.unsubscribe_all()
    logger.info("Done executing scan")


def execute_scan_2d(
    inner_scan,
    outter_scan,
    abort_signal,
    sample=None,
    print_outter_msg=False,
    scan_name="",
    verbose=False,
    recover_y_piezo=False,
):
    """Execute a 2D scan with monitoring.

    Parameters:
        inner_scan: Inner scan object.
        outter_scan: Outer scan object.
        print_outter_msg (bool): Whether to print outer loop messages.
        scan_name (str): Name of the scan.
        adjust_samx_speed (bool): Whether to adjust samx speed during the scan.
        recover_y_piezo (bool): Center sample.y.piezo after each inner scan if
            sample.y.piezo_value exceeds sample.y.piezo_max_value.
    """
    watcher = ScanMonitor(
        numpts_x=inner_scan.number_points.value,
        numpts_y=outter_scan.number_points.value,
        scan_name=scan_name.zfill(SCANNUM_DIGITS),
        sample=sample,
        verbose=verbose,
        execute_signal=outter_scan.execute_scan,
        pause_signal=outter_scan.wait,
        abort_signal=abort_signal,
        recover_y_piezo=recover_y_piezo,
        name=f"{outter_scan.name}_monitor",
    )
    watcher.outter_print_msg = print_outter_msg
    watcher.has_outer_loop = True

    logger.info("Done setting up scan, about to start scan")
    logger.info("Start executing scan")

    outter_scan.execute_scan.subscribe(watcher.watch_execute_scan)  # Subscribe to the scan
    outter_scan.current_point.subscribe(watcher.watch_counter_outter)
    outter_scan.scan_phase.subscribe(watcher.watch_faze_outer)
    inner_scan.execute_scan.subscribe(watcher.watch_inner_execute_scan)
    inner_scan.current_point.subscribe(watcher.watch_counter_inner)
    inner_scan.scan_phase.subscribe(watcher.watch_faze_inner)

    try:
        # Safe rewind boundary: resume should re-enter waiting/trigger handling,
        # not replay upstream scanrecord staging/configuration.
        yield from bps.checkpoint()
        yield from bps.trigger(watcher, wait=True)
    except BaseException:
        watcher.stop(success=False)
        raise
    finally:
        inner_scan.current_point.unsubscribe_all()
        inner_scan.scan_phase.unsubscribe_all()
        inner_scan.execute_scan.unsubscribe_all()
        outter_scan.current_point.unsubscribe_all()
        outter_scan.scan_phase.unsubscribe_all()
        outter_scan.execute_scan.unsubscribe_all()
    logger.info("Done executing scan")

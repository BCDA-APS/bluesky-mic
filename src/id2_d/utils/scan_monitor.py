"""
Creating a list of scan monitoring function so that Bluesky Plans can subscribe to it

@author: yluo(grace227)

List of functions::

    # # watch_counter( ... ): # Monitor and log the counter value

"""

import logging
import time

import bluesky.plan_stubs as bps
from apstools.plans import run_blocking_function
from ophyd.status import Status

logger = logging.getLogger(__name__)

SCANNUM_DIGITS = 4


class ScanMonitor:
    """Monitor and track scan progress and timing for Bluesky scans."""

    current_line = 0
    line_time_in = 0
    line_time_out = 0
    line_delta = 0
    scan_time_remaining = 0
    outter_print_msg = False

    def __init__(self, numpts_x=None, scan_name=None, numpts_y=0):
        """Initialize the ScanMonitor with scan parameters.

        Parameters
        ----------
        numpts_x : int, optional
            Number of points in the x direction.
        scan_name : str, optional
            Name of the scan.
        numpts_y : int, optional
            Number of points in the y direction.
        """
        self.scan_active = False
        self.counter_active = False
        self.st = Status()
        self.numpts_x = numpts_x
        self.numpts_y = numpts_y
        self.scan_name = scan_name
        self.scan_faze = ""

    def update_scan_phase(self, value, enum_strs, **kwargs):
        """Update the scan phase based on the value and enum strings.

        Parameters
        ----------
        value : int
            Enum value representing the scan phase.
        enum_strs : list
            List of enum strings for scan phases.
        **kwargs
            Additional keyword arguments.
        """
        status = enum_strs[value]
        # logger.info(f"Scan status: {status}")
        self.scan_faze = status

        if status == "SCAN_DONE":
            self.st.set_finished()
            logger.info(f"FINISHED: ScanMonitor.st {self.st}")

    def update_eta(self):
        """Update the estimated time remaining for the scan."""
        self.line_time_out = time.perf_counter()
        self.line_delta = round(self.line_time_out - self.line_time_in, 2)
        self.line_time_in = self.line_time_out

    def watch_counter_outter(self, old_value, value, **kwargs):
        if self.counter_active:
            if value >= 1:
                self.update_eta()
                self.scan_time_remaining = round(
                    (self.numpts_y - value) * self.line_delta, 2
                )
                self.current_line = value
                if self.outter_print_msg:
                    prog = round(100 * value / self.numpts_y, 2)
                    msg = f"Filename: {self.scan_name}, Scan_progress: {prog}%, "
                    msg += f"Scanned : {value}/{self.numpts_y}, Scan_remaining : {self.scan_time_remaining}, "
                    msg += f"Line_eta : {self.line_delta}"
                    logger.info(msg)

    def watch_counter_inner(self, old_value, value, **kwargs):
        if self.counter_active and self.numpts_x is not None:
            if all([value > 0, value > old_value, value < self.numpts_x]):
                if self.numpts_y == 0:
                    self.update_eta()
                    self.scan_time_remaining = round(
                        (self.numpts_x - value) * self.line_delta, 2
                    )
                    prog = round(100 * value / self.numpts_x, 2)
                    msg = f"Filename: {self.scan_name}, Scan_progress: {prog}%, "
                    msg += f"Line: 1/1, Scan_remaining: {self.scan_time_remaining}, "
                    msg += f"Scanned {value}/{self.numpts_x}"
                    logger.info(msg)
                    # logger.info(f"Scan progress: {self.scan_name}: {prog}% :, scanned {value}/{self.numpts_x}")
                else:
                    prog = round(
                        100
                        * (self.numpts_x * self.current_line + value)
                        / (self.numpts_x * self.numpts_y),
                        2,
                    )
                    msg = (
                        f"Filename: {self.scan_name}, Scan_progress: {prog}%, "
                        f"Line: {self.current_line}/{self.numpts_y}, "
                        f"Scan_remaining: {self.scan_time_remaining}, "
                        f"Line_eta: {self.line_delta}, "
                        f"Scanned: {value}/{self.numpts_x}"
                    )
                    logger.info(msg)

    def watch_execute_scan(self, old_value, value, **kwargs):
        if self.scan_active and old_value == 1 and value == 0:
            self.st.set_finished()
            logger.info(f"FINISHED: ScanMonitor.st {self.st}")
            logger.info(f"Scan phase: {self.scan_faze}")


# Usage
def execute_scan_1d(scan1, scan_name=""):
    watcher = ScanMonitor(
        numpts_x=scan1.number_points.value, scan_name=scan_name.zfill(SCANNUM_DIGITS)
    )

    logger.info("Done setting up scan, about to start scan")
    logger.info("Start executing scan")
    print(watcher.scan_name)

    scan1.execute_scan.subscribe(watcher.watch_execute_scan)  # Subscribe to the scan
    scan1.number_points_rbv.subscribe(watcher.watch_counter_inner)

    try:
        yield from bps.mv(scan1.execute_scan, 1)  # Start scan
        watcher.scan_active = True
        watcher.counter_active = True
        watcher.line_time_in = time.perf_counter()
        yield from run_blocking_function(watcher.st.wait)
    finally:
        scan1.number_points_rbv.unsubscribe_all()
        scan1.execute_scan.unsubscribe_all()
    logger.info("Done executing scan")


def execute_scan_2d(inner_scan, outter_scan, print_outter_msg=False, scan_name=""):
    watcher = ScanMonitor(
        numpts_x=inner_scan.number_points.value,
        numpts_y=outter_scan.number_points.value,
        scan_name=scan_name.zfill(SCANNUM_DIGITS),
    )
    watcher.outter_print_msg = print_outter_msg

    logger.info("Done setting up scan, about to start scan")
    logger.info("Start executing scan")

    outter_scan.scan_phase.subscribe(watcher.update_scan_phase)
    # outter_scan.execute_scan.subscribe(
    #     watcher.watch_execute_scan
    # )  # Subscribe to the scan
    outter_scan.number_points_rbv.subscribe(watcher.watch_counter_outter)
    inner_scan.number_points_rbv.subscribe(watcher.watch_counter_inner)

    try:
        yield from bps.mv(outter_scan.execute_scan, 1)  # Start scan
        watcher.scan_active = True
        watcher.counter_active = True
        watcher.line_time_in = time.perf_counter()
        yield from run_blocking_function(watcher.st.wait)
    finally:
        inner_scan.number_points_rbv.unsubscribe_all()
        outter_scan.number_points_rbv.unsubscribe_all()
        outter_scan.execute_scan.unsubscribe_all()

    yield from bps.sleep(1)
    logger.info("Done executing scan")

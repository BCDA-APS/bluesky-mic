"""
Creating a list of scan monitoring function so that Bluesky Plans can subscribe to it

@author: yluo(grace227)

List of functions::

    # # watch_counter( ... ): # Monitor and log the counter value

"""

from ophyd.status import Status
import bluesky.plan_stubs as bps
from apstools.plans import run_blocking_function
import logging
import time

logger = logging.getLogger(__name__)


class ScanMonitor:
    current_line = 0
    line_time_in = 0
    line_time_out = 0
    line_delta = 0
    scan_time_remaining = 0

    def __init__(self, numpts_x=None, scan_name=None, numpts_y=0):
        self.scan_active = False
        self.counter_active = False
        self.st = Status()
        self.numpts_x = numpts_x
        self.numpts_y = numpts_y
        self.scan_name = scan_name

    def update_eta(self):
        self.line_time_out = time.perf_counter()
        self.line_delta = round(self.line_time_out - self.line_time_in, 2)
        self.line_time_in = self.line_time_out

    def watch_counter_outter(self, old_value, value, **kwargs):
        if self.counter_active:
            self.current_line = value
            if value > 1:
                self.update_eta()
                self.scan_time_remaining = round((self.numpts_y - value) * self.line_delta, 2)

    def watch_counter_inner(self, old_value, value, **kwargs):
        if self.counter_active and self.numpts_x is not None:
            if all([value > 0, value > old_value, value < self.numpts_x]):
                if self.numpts_y == 0:
                    self.update_eta()
                    self.scan_time_remaining = round((self.numpts_x - value) * self.line_delta, 2)
                    prog = round(100 * value / self.numpts_x, 2)
                    msg = f"Scan progress: {self.scan_name}: {prog}% : "
                    msg += f"line 1/1 : scan remaining {self.scan_time_remaining} : "
                    msg += f"scanned {value}/{self.numpts_x}"
                    logger.info(msg)
                    # logger.info(f"Scan progress: {self.scan_name}: {prog}% :, scanned {value}/{self.numpts_x}")
                else:
                    prog = round(
                        100 * (self.numpts_x * self.current_line + value) / (self.numpts_x * self.numpts_y), 2
                    )
                    msg = f"Scan progress: {self.scan_name}: {prog}% : "
                    msg += f"line {self.current_line}/{self.numpts_y} : scan remaining {self.scan_time_remaining} : "
                    msg += f"line eta {self.line_delta} : "
                    msg += f"scanned {value}/{self.numpts_x}"

                    logger.info(msg)

    def watch_execute_scan(self, old_value, value, **kwargs):
        if self.scan_active and old_value == 1 and value == 0:
            self.st.set_finished()
            logger.info(f"FINISHED: ScanMonitor.st {self.st}")


# Usage
def execute_scan_1d(scan1, scan_name=""):
    watcher = ScanMonitor(numpts_x=scan1.number_points.value, scan_name=scan_name)

    logger.info("Done setting up scan, about to start scan")
    logger.info("Start executing scan")

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


def execute_scan_2d(inner_scan, outter_scan, scan_name=""):
    watcher = ScanMonitor(
        numpts_x=inner_scan.number_points.value, numpts_y=outter_scan.number_points.value, scan_name=scan_name
    )

    logger.info("Done setting up scan, about to start scan")
    logger.info("Start executing scan")

    outter_scan.execute_scan.subscribe(watcher.watch_execute_scan)  # Subscribe to the scan
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
    logger.info("Done executing scan")

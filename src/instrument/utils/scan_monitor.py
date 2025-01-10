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

logger = logging.getLogger(__name__)


class ScanMonitor:
    def __init__(self, numpts_x):
        self.scan_active = False
        self.counter_active = False
        self.st = Status()
        self.numpts_x = numpts_x

    def watch_counter(self, old_value, value, **kwargs):
        if self.counter_active:
            if all([value > 0, value > old_value, value < self.numpts_x]):
                prog = round(100 * value / self.numpts_x, 2)
                logger.info(f"Scan progress: {prog}% done, scanned {value}/{self.numpts_x}")

    def watch_execute_scan(self, old_value, value, **kwargs):
        if self.scan_active and old_value == 1 and value == 0:
            self.st.set_finished()
            logger.info(f"FINISHED: ScanMonitor.st {self.st}")


# Usage
def execute_scan(scan1, numpts_x):
    watcher = ScanMonitor(numpts_x)

    logger.info("Done setting up scan, about to start scan")
    logger.info("Start executing scan")

    scan1.execute_scan.subscribe(watcher.watch_execute_scan)  # Subscribe to the scan
    scan1.number_points_rbv.subscribe(watcher.watch_counter)

    try:
        yield from bps.mv(scan1.execute_scan, 1)  # Start scan
        watcher.scan_active = True
        watcher.counter_active = True
        yield from run_blocking_function(watcher.st.wait)
    finally:
        scan1.number_points_rbv.unsubscribe_all()
        scan1.execute_scan.unsubscribe_all()
    logger.info("Done executing scan")

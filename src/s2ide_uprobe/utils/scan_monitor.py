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
    """Monitor and log scan progress.

    Attributes:
        current_line (int): Current line being scanned.
        line_time_in (float): Time when line scan started.
        line_time_out (float): Time when line scan ended.
        line_delta (float): Time taken for line scan.
        scan_time_remaining (float): Estimated remaining scan time.
        outter_print_msg (bool): Whether to print outer loop messages.
    """

    current_line = 0
    line_time_in = 0
    line_time_out = 0
    line_delta = 0
    scan_time_remaining = 0
    outter_print_msg = False
    hydra = None
    sis3820 = None
    outter_scan = None
    inner_scan = None
    xmap = None

    def __init__(self, outter_scan=None, inner_scan=None, 
                 scan_name=None, hydra=None, sis3820=None,  
                 xmap=None):
        
        """Initialize ScanMonitor.
        
        Parameters:
            outter_scan (ScanRecord, optional): Ophyd outter scanrecord.
            inner_scan (ScanRecord, optional): Ophyd inner scanrecord.
            scan_name (str, optional): Name of the scan.
            hydra (Hydra, optional): Ophyd hydra device.
            sis3820 (SIS3820, optional): Ophyd sis3820 device.
            xmap (XMap, optional): Ophyd xmap device.
        """
        
        self.scan_active = False
        self.counter_active = False
        self.st = Status()
        self.outter_scan = outter_scan
        self.inner_scan = inner_scan
        self.numpts_x = inner_scan.number_points.get()
        self.numpts_y = outter_scan.number_points.get()
        self.scan_name = scan_name
        self.hydra = hydra
        self.sis3820 = sis3820
        self.xmap = xmap

    def update_eta(self):
        """Update estimated time remaining."""
        self.line_time_out = time.perf_counter()
        self.line_delta = round(self.line_time_out - self.line_time_in, 2)
        self.line_time_in = self.line_time_out

    def watch_counter_outter(self, value, old_value, **kwargs):
        """Monitor outer loop counter.

        Parameters:
            old_value (int): Previous counter value.
            value (int): Current counter value.
            **kwargs: Additional keyword arguments.
        """

        logger.info("watch_counter_outter called")
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
                    msg += (
                        f"Scanned : {value}/{self.numpts_y}, "
                        f"Scan_remaining : {self.scan_time_remaining}, "
                    )
                    msg += f"Line_eta : {self.line_delta}"
                    logger.info(msg)
                if self.hydra is not None:
                    yield from self.hydra.set_send_parameters(1)
                    logger.info(f"Send parameters to {self.hydra.prefix}")

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
                    self.scan_time_remaining = round(
                        (self.numpts_x - value) * self.line_delta, 2
                    )
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
        if self.scan_active and old_value == 1 and value == 0:
            self.st.set_finished()
            logger.info(f"FINISHED: ScanMonitor.st {self.st}")


# Usage
def execute_scan_1d(scan1, scan_name=""):
    """Execute a 1D scan with monitoring.

    Parameters:
        scan1: Scan object.
        scan_name (str): Name of the scan.
    """
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


def execute_scan_2d(inner_scan, outter_scan, print_outter_msg=False, scan_name="",
                    hydra=None, sis3820=None, xmap=None):
    """Execute a 2D scan with monitoring.

    Parameters:
        inner_scan: Inner scan scanrecord.
        outter_scan: Outer scan scanrecord.
        print_outter_msg (bool): Whether to print outer loop messages.
        scan_name (str): Name of the scan.
        hydra (Hydra, optional): Ophyd hydra device.
        sis3820 (SIS3820, optional): Ophyd sis3820 device.
        xmap (XMap, optional): Ophyd xmap device.
    """

    watcher = ScanMonitor(
        scan_name=scan_name.zfill(SCANNUM_DIGITS),
        hydra=hydra,
        sis3820=sis3820,
        outter_scan=outter_scan,
        inner_scan=inner_scan,
        xmap=xmap,
    )
    watcher.outter_print_msg = print_outter_msg

    logger.info("Done setting up scan, about to start scan")
    logger.info("Start executing scan")

    outter_scan.execute_scan.subscribe(
        watcher.watch_execute_scan
    )  # Subscribe to the scan
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

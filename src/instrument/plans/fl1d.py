import time

import bluesky.plan_stubs as bps
from apstools.plans import run_blocking_function
from ophyd import EpicsSignalRO
from ophyd.status import Status

from ..devices.scan_record import ScanRecord
from .plan_blocks import count_subscriber
from .plan_blocks import watch_counter

# Create Required Devices for Fly Scan
# scanrecord1 = ScanRecord("eac99:scan1", name="er_test")
counter = EpicsSignalRO("eac99:scan1.CPT", name = "counter")
scanrecord1 = ScanRecord("eac99:scan1", name="er_test")


def fly(
    samplename="smp1",
    user_comments="",
    # scanrecord1_pv="2idsft:scan1",
    # scanrecord2_pv="2idsft:scan2",
    scanrecord1_pv="eac99:scan1",
    width=0,
    height=0,
    x_center=None,
    y_center=None,
    stepsize_x=0,
    stepsize_y=0,
    dwell=0,
    smp_theta=None,
    xrf_on=True,
    ptycho_on=False,
    preamp_on=False,
    fpga_on=False,
    position_stream=False,
    eta=0,
):
    def watch_execute_scan(old_value, value, **kwargs):
        if old_value == 1 and value == 0:
            st.set_finished()
            scanrecord1.execute_scan.clear_sub(watch_execute_scan)

        counter.unsubscribe(watch_counter)

    """Start executing scan"""
    print("Done setting up scan, about to start scan")

    st = Status()

    time.sleep(2)
    ready = True
    while not ready:
        time.sleep(1)

    print("executing scan")

    scanrecord1.execute_scan.subscribe(watch_execute_scan)  # Subscribe to the scan
    # executor

    yield from bps.mv(scanrecord1.execute_scan, 1)  # Start scan
    yield from bps.sleep(1)  # Empirical, for the IOC
    yield from count_subscriber(counter, scanrecord1) # Counter Subscriber

    yield from run_blocking_function(st.wait)

    print("end of plan")

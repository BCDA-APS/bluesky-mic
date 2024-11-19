import time
from collections import deque

import bluesky.plan_stubs as bps
from apstools.plans import run_blocking_function
from bluesky import preprocessors as bpp
from ophyd import EpicsSignalRO
from ophyd import Signal
from ophyd.status import Status

from ..devices.scan_record import ScanRecord

# Create Required Devices for Fly Scan
scanrecord1 = ScanRecord("eac99:scan1", name="er_test")
flag = Signal(name="flag", value=True)
counter = EpicsSignalRO("eac99:scan1.CPT", name = "counter")


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

    def watch_counter(value=None, **kwargs):
        flag.put(True)  # new value available

    def take_reading():
        yield from bps.create(name="primary")
        try:
            yield from bps.read(counter)
        except Exception as reason:
            print(reason)
        yield from bps.save()

    @bpp.run_decorator(md={})
    def count_subscriber():
        counter.subscribe(watch_counter) # Collect a new event each time the scaler updates
        while counter.value <= 11:
            if flag.get():
                yield from take_reading()
                yield from bps.mv(flag, False)  # reset the flag
                if counter.value == 11:
                    break
            yield from bps.sleep(0.1)

        counter.unsubscribe(watch_counter)

    """Start executing scan"""
    print("Done setting up scan, about to start scan")

    st = Status()

    time.sleep(2)
    ready = True
    while not ready:
        time.sleep(1)

    print("executing scan")

    scanrecord1.execute_scan.subscribe(watch_execute_scan) # Subscribe to the scan
                                                           # executor

    yield from bps.mv(scanrecord1.execute_scan, 1) # Start scan
    yield from bps.sleep(1)  # Empirical, for the IOC
    yield from count_subscriber() # Counter Subscriber

    yield from run_blocking_function(st.wait)

    print("end of plan")


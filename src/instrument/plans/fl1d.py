import time

import bluesky.plan_stubs as bps
from apstools.plans import run_blocking_function
from bluesky import plans as bp
from ophyd import Component as Cpt
from ophyd.device import Device
from ophyd import EpicsSignalRO
from ophyd.status import Status
from collections import deque

from bluesky.callbacks import LiveTable
from ..devices.scan_record import ScanRecord

from bluesky import preprocessors as bpp
from ophyd import Signal
from ophyd.scaler import ScalerChannel

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

    scanrecord1 = ScanRecord(scanrecord1_pv, name="er_test")


    """Start executing scan"""
    print("Done setting up scan, about to start scan")

    st = Status()

    # TODO: needs monitoring function incase detectors stall or one of teh iocs crashes
    # monitor trigger count and compare against detector saved frames count. s

    def watch_execute_scan(old_value, value, **kwargs):
        # Watch for scan1.EXSC to change from 1 to 0 (when the scan ends).

        if old_value == 1 and value == 0:
            # mark as finished (successfully).
            # yield from bp.count([counter], num=100,delay=0.05)

            st.set_finished()
            # Remove the subscription.
            scanrecord1.execute_scan.clear_sub(watch_execute_scan)


    # TODO need some way to check if devices are ready before proceeding. timeout and
    #   exit with a warning if something is missing.
    # if motors.inpos and pm1.isready and tmm.isready and xp3.isready and sgz.isready and postrm.isready:  # noqa: E501

    time.sleep(2)
    ready = True
    while not ready:
        time.sleep(1)

    print("executing scan")

    scanrecord1.execute_scan.subscribe(watch_execute_scan)


    yield from bps.mv(scanrecord1.execute_scan, 1)

    flag = Signal(name="flag", value=True)
    counter = EpicsSignalRO("eac99:scan1.CPT", name = "counter")
    # counter = ScalerChannel("eac99:scan1.CPT", name="scaler")

    def watcher(value=None, **kwargs):
        # print(f"{value=:.3f}")
        flag.put(True)  # new value available

    def take_reading():
        # print(m1.read())
        yield from bps.create(name="primary")
        try:
            yield from bps.read(counter)
        except Exception as reason:
            print(reason)
        yield from bps.save()

    @bpp.run_decorator(md={})
    def _fly_it():
        # Collect a new event each time the scaler updates
        counter.subscribe(watcher)
        # yield from bps.mv(counter.count, 1)  # push the Count button
        while counter.value != 11:
            if flag.get():
                yield from take_reading()
                yield from bps.mv(flag, False)  # reset the flag
            yield from bps.sleep(0.1)
        counter.unsubscribe(watcher)

    # yield from bps.mv(counter.preset_time, scan_time)
    yield from bps.sleep(1)  # empirical, for the IOC

    yield from _fly_it()

    yield from run_blocking_function(st.wait)

    print("end of plan")


def fly_plan(motion_offset=10, scan_time=10, period=0.1, velocity=0.1):
    flag = Signal(name="flag", value=True)
    counter = EpicsSignalRO("eac99:scan1.CPT", name = "counter")
    # counter = ScalerChannel("eac99:scan1.CPT", name="scaler")

    def watcher(value=None, **kwargs):
        # print(f"{value=:.3f}")
        flag.put(True)  # new value available

    def take_reading():
        # print(m1.read())
        yield from bps.create(name="primary")
        try:
            yield from bps.read(counter)
        except Exception as reason:
            print(reason)
        yield from bps.save()

    @bpp.run_decorator(md={})
    def _fly_it():
        # Collect a new event each time the scaler updates
        counter.subscribe(watcher)
        # yield from bps.mv(counter.count, 1)  # push the Count button
        while counter.value != 12:
            if flag.get():
                yield from take_reading()
                yield from bps.mv(flag, False)  # reset the flag
            yield from bps.sleep(period)
        counter.unsubscribe(watcher)

    # yield from bps.mv(counter.preset_time, scan_time)
    yield from bps.sleep(1)  # empirical, for the IOC

    yield from _fly_it()

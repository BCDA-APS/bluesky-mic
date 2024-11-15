import time

import bluesky.plan_stubs as bps
from apstools.plans import run_blocking_function
from bluesky import plans as bp
from ophyd import Component as Cpt
from ophyd.device import Device
from ophyd import EpicsSignalRO
from ophyd.status import Status
from collections import deque


from ..devices.scan_record import ScanRecord


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

    def accumulate(value, old_value, timestamp, **kwargs):
        readings.append({"counter": {"value": value, "timestamp": timestamp}})
    readings = deque(maxlen=5)

    yield from bps.mv(scanrecord1.execute_scan, 1)

    ######### Desired logic for below
    # while yield from run_blocking_function(st.wait)
    #     print("test")
    def monitor_x_for(duration):
        yield from bps.monitor(counter, name="x_monitor")
        yield from bps.sleep(duration)  # Wait for readings to accumulate.
        yield from bps.unmonitor(counter)
        yield from bps.close_run()
    # pvdet = PVdet("eac99:scan1", name="pvdet")
    # yield from bp.count([pvdet],)
    # counter= scanrecord1.current_point
    counter = EpicsSignalRO("eac99:scan1.CPT", name = "counter")
    # counter.subscribe(accumulate)

    # yield from bp.count([counter], num=100,delay=0.05)
    yield from monitor_x_for(1)
    #########

    yield from run_blocking_function(st.wait)

    print("end of plan")


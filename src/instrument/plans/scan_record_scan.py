"""
Creating a bluesky plan that interacts with Scan Record.

EXAMPLE::

    # Load this code in IPython or Jupyter notebook:
    %run -i user/scan_record_2idd.py

    # Run the plan with the RunEngine:
    RE(scan_record2(scanrecord_name = 'scan1', ioc = "2idsft:", m1_name = 'm1',
                   m1_start = -0.5, m1_finish = 0.5,
                   m2_name = 'm3', m2_start = -0.2 ,m2_finish = 0.2,
                   npts = 50, dwell_time = 0.1))
"""

__all__ = """
    scan_record_isn
""".split()

import logging

import bluesky.plan_stubs as bps
import numpy as np
from apstools.plans import run_blocking_function
from apstools.synApps import SscanRecord
from epics import caput
from ophyd.status import Status

logger = logging.getLogger(__name__)
logger.info(__file__)


print("Creating RE plan that uses scan record")


def setup_scan1(
    scan1,
    scanrecord_name,
    ioc,
    m1_name,
    m2_name,
    m1_start,
    m1_finish,
    m2_start,
    m2_finish,
    npts,
    dwell_time,
):
    print("in setup_scan function")
    scan1.wait_for_connection()
    # yield from bps.mv(scaler1.preset_time, ct)  # counting time/point
    yield from run_blocking_function(scan1.reset)
    yield from bps.sleep(0.2)  # arbitrary wait for EPICS to finish the reset.

    # scan1.positioners.p1.P1PA not found...
    # using EpicsSignal directly
    m1_arr = np.linspace(m1_start, m1_finish, npts)
    m2_arr = np.linspace(m2_start, m2_finish, npts)
    xx, yy = np.meshgrid(m1_arr, m2_arr)
    caput(f"{ioc}{scanrecord_name}.P1PA", xx.flatten())
    caput(f"{ioc}{scanrecord_name}.P2PA", yy.flatten())
    # p1pa = EpicsSignal(f"{scan1.prefix}.P1PA", name='p1pa')
    # p2pa = EpicsSignal(f"{scan1.prefix}.P2PA", name='p2pa')
    # p1pa.wait_for_connection()
    # p2pa.wait_for_connection()
    # yield from bps.mv(p1pa, xx.flatten(), p2pa, yy.flatten())
    npts_tot = int(npts * npts)

    # positioners
    yield from bps.mv(
        scan1.positioners.p1.mode,
        1,
        scan1.positioners.p1.readback_pv,
        f"{ioc}{m1_name}.RBV",
        scan1.positioners.p1.setpoint_pv,
        f"{ioc}{m1_name}",
        scan1.positioners.p2.mode,
        1,
        scan1.positioners.p2.readback_pv,
        f"{ioc}{m2_name}.RBV",
        scan1.positioners.p2.setpoint_pv,
        f"{ioc}{m2_name}",
        scan1.positioner_delay,
        dwell_time,
        scan1.number_points,
        npts_tot,
    )
    print("exit in setup_scan function")


def scan_record_isn(
    scanrecord_name="scan1",
    ioc="2idsft:",
    m1_name="m1",
    m1_start=-0.5,
    m1_finish=0.5,
    m2_name="m3",
    m2_start=-0.2,
    m2_finish=0.2,
    npts=50,
    dwell_time=0.1,
):
    """Simple bluesky plan for demonstrating 2D raster scan."""
    param_labels = [
        "scanrecord_name",
        "ioc",
        "m1_name",
        "m1_start",
        "m1_finish",
        "m2_name",
        "m2_start",
        "m2_finish",
        "npts",
        "dwell_time",
    ]
    for l in param_labels:
        print(f"plan starts with {l}={eval(l)}")

    """Set up scan record"""
    print("in setup_scan function")
    scan1 = SscanRecord(f"{ioc}{scanrecord_name}", name=scanrecord_name)
    yield from setup_scan1(
        scan1,
        scanrecord_name,
        ioc,
        m1_name,
        m2_name,
        m1_start,
        m1_finish,
        m2_start,
        m2_finish,
        npts,
        dwell_time,
    )

    """Start executing scan"""
    # st = Status(timeout=20)
    st = Status()
    print("Done setting up scan record, about to start scan")

    def watch_execute_scan(old_value, value, **kwargs):
        # Watch for scan1.EXSC to change from 1 to 0 (when the scan ends).
        if old_value == 1 and value == 0:
            # mark as finished (successfully).
            st.set_finished()
            # Remove the subscription.
            scan1.execute_scan.clear_sub(watch_execute_scan)

    yield from bps.mv(scan1.execute_scan, 1)
    scan1.execute_scan.subscribe(watch_execute_scan)
    yield from run_blocking_function(st.wait)

    print("end of plan\n")

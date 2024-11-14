import time

import bluesky.plan_stubs as bps
from apstools.plans import run_blocking_function
from bluesky import plans as bp
from ophyd.status import Status

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

    noisy_det = SynGauss(
        "noisy_det",
        motor,
        "motor",
        center=0,
        Imax=1,
        noise="uniform",
        sigma=1,
        noise_multiplier=0.1,
        labels={"detectors"},
    )

    yield from bps.mv(scanrecord1.execute_scan, 1)

    ######### Desired logic for below
    # while yield from run_blocking_function(st.wait)
    #     print("test")
    yield from bp.count([scanrecord1.current_point.value])

    #########

    yield from run_blocking_function(st.wait)

    print("end of plan")

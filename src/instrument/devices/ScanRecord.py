__all__ = """
    scan1
    scan2
    setup_scanrecord
""".split()
from apstools.synApps import SscanRecord
from ophyd import Device, EpicsSignal, Component
from apstools.plans import run_blocking_function
from epics import caput, caget
import bluesky.plan_stubs as bps
import logging
logger = logging.getLogger(__name__)
logger.info(__file__)

def setup_scanrecord(scan1, scan2, scan_type, m1_name, m2_name, xarr, yarr, dwell_time, loop1_npts, trigger1="", trigger2="", trigger3="", trigger4="",):
    
    print("in setup_scan function")
    scan1.wait_for_connection()
    scan2.wait_for_connection()
    # yield from bps.mv(scaler1.preset_time, ct)  # counting time/point
    yield from run_blocking_function(scan1.reset)
    yield from run_blocking_function(scan2.reset)
    yield from bps.sleep(0.2)  # arbitrary wait for EPICS to finish the reset.

    caput(f"{scan1.prefix}.P1PA", list(xarr))
    caput(f"{scan2.prefix}.P1PA", list(yarr))

    if scan_type=="fly":
        yield from bps.mv(scan1.positioner_delay, 0) #if fly scanning, positioner move at speed=step_size/dwell_time, no delay needed
    else: 
        yield from bps.mv(scan1.positioner_delay, dwell_time) #if step scanning, positioners move at 'fast' speed and dwell for specified dwell time at each position.
    
    # positioners
    yield from bps.mv(
        scan1.positioners.p1.mode, 1,
        scan1.positioners.p1.readback_pv, f"{m1_name}.RBV",
        scan1.positioners.p1.setpoint_pv, f"{m1_name}",
        scan1.number_points, len(xarr),
        scan2.positioners.p1.mode, 1,
        scan2.positioners.p1.readback_pv, f"{m2_name}.RBV",
        scan2.positioners.p1.setpoint_pv, f"{m2_name}",
        scan2.number_points, len(yarr),
        scan2.triggers.t1.trigger_pv, trigger1,
        scan2.triggers.t2.trigger_pv, trigger2,
        scan2.triggers.t3.trigger_pv, trigger3,
        scan2.triggers.t4.trigger_pv, trigger4,
    )

scan1 = SscanRecord("2idsft:scan1", name="scan1")
scan2 = SscanRecord("2idsft:scan2", name="scan2")
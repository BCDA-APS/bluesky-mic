__all__ = """
    scan1
    scan2
""".split()

from .. import iconfig
from apstools.synApps import SscanRecord
from ophyd import Device, EpicsSignal, Component
from apstools.plans import run_blocking_function
from epics import caput, caget
import bluesky.plan_stubs as bps
import logging
logger = logging.getLogger(__name__)
logger.info(__file__)

class myScanRecord(SscanRecord):
    def __init__(self): 
        self.p1pa = EpicsSignal(name="positions_array")

    def setup_scan1(self, scan_type, m1_name, arr, dwell_time):
        self.wait_for_connection()

        yield from run_blocking_function(self.reset)
        yield from bps.sleep(0.2)  # arbitrary wait for EPICS to finish the reset.

        if scan_type=="fly": #for scan1 only
            yield from bps.mv(self.positioner_delay, 0) #if fly scanning, positioner move at speed=step_size/dwell_time, no delay needed
        else: 
            yield from bps.mv(self.positioner_delay, dwell_time) #if step scanning, positioners move at 'fast' speed and dwell for specified dwell time at each position.
        
        yield from bps.mv(
            self.p1pa,list(arr),
            self.positioners.p1.mode, 1,
            self.positioners.p1.readback_pv, f"{m1_name}.RBV",
            self.positioners.p1.setpoint_pv, f"{m1_name}",
            self.number_points, len(arr),
        )

    def setup_scan2(self, m2_name, arr, trigger1="", trigger2="", trigger3="", trigger4=""):
        print("in setup_scan function")
        self.wait_for_connection()

        yield from run_blocking_function(self.reset)
        yield from bps.sleep(0.2)  # arbitrary wait for EPICS to finish the reset.
        yield from bps.mv(
            self.positioners.p1.mode, 1,
            self.positioners.p1.readback_pv, f"{m2_name}.RBV",
            self.positioners.p1.setpoint_pv, f"{m2_name}",
            self.number_points, len(arr),
            self.triggers.t1.trigger_pv, trigger1,
            self.triggers.t2.trigger_pv, trigger2,
            self.triggers.t3.trigger_pv, trigger3,
            self.triggers.t4.trigger_pv, trigger4,
        )

scan1_pv = iconfig.get("SCAN1")
scan2_pv = iconfig.get("SCAN2")
scan1 = myScanRecord(scan1_pv, name="scan1")
scan2 = myScanRecord(scan1_pv, name="scan2")
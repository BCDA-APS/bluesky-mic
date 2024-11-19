"""
Scan Record Ophyd Device Class & Instatiation
"""

import logging

import bluesky.plan_stubs as bps
from apstools.synApps import SscanRecord
from epics import PV
from ophyd import Component
from ophyd import EpicsSignal, EpicsSignalRO

logger = logging.getLogger(__name__)
logger.info(__file__)


class ScanRecord(SscanRecord):
    """
    Scan Record Device Class
    """

    P1SM = Component(EpicsSignal, ".P1SM")
    P1AR = Component(EpicsSignal, ".P1AR")
    P1CP = Component(EpicsSignal, ".P1CP")
    P1SI = Component(EpicsSignal, ".P1SI")
    P1WD = Component(EpicsSignal, ".P1WD")

    # number_of_points_readback = Component(EpicsSignal, ".P1WD") #TODO: Add as area detector
    # number_of_points_readback = Component(EpicsSignal, ".P1WD")

    def __init__(self, *args, **kwargs):
        """
        Init Device parent class and instatiate P1PA PV
        """
        super().__init__(*args, **kwargs)
        self.P1PA = PV(f"{self.prefix}.P1PA")

    def set_scan_mode(self, mode):
        """
        set scan mode
        """
        describe = self.P1SM.describe().popitem()
        states = describe[1]["enum_strs"]
        mode = mode.upper()
        if mode in states:
            idx = states.index(mode)
            yield from bps.mv(self.P1SM, idx)
            logger.info(f"Assigning scan mode in {self.prefix} to {mode}.")
        else:
            logger.error(
                f"Not able to find the desired scan mode: {mode} in {self.prefix}"
            )

    def set_rel_abs_motion(self, mode):
        """
        set relative absolute motion
        """
        describe = self.P1AR.describe().popitem()
        states = describe[1]["enum_strs"]
        mode = mode.upper()
        if mode in states:
            idx = states.index(mode)
            yield from bps.mv(self.P1AR, idx)
            logger.info(f"Assigning scan motion in {self.prefix} to {mode}.")
        else:
            logger.error(
                f"Not able to find the desired scan motion: {mode} in {self.prefix}"
            )

    def set_center_width_stepsize(self, center: float, width: float, ss: float):
        """
        set center width stepsize
        """
        try:
            yield from bps.mv(
                self.P1CP,
                center,
                self.P1SI,
                ss,
                self.P1WD,
                width,
            )
            logger.info(
                f"Setting scan record {self.prefix} to have {center=}, {width=}, stepsize={ss}"  # noqa: E501
            )
        except Exception as e:
            logger.error(
                f"{e} \n "
                + f"Setting scan record {self.prefix} to have {center=}, {width=}, stepsize={ss}"  # noqa: E501
            )

    # def set_scan_range()

    # def __init__(self, pvname, name = None):
    #     self.pvname = pvname
    #     self.P1PA = PV(f"{self.pvname}.P1PA")

    # p1pa = EpicsSignal(name="positions_array")

    # def setup_scan1(self, scan_type, m1_name, arr, dwell_time):
    #     self.wait_for_connection()

    #     yield from run_blocking_function(self.reset)
    #     yield from bps.sleep(0.2)  # arbitrary wait for EPICS to finish the reset.

    #     if scan_type=="fly": #for scan1 only
    #         yield from bps.mv(self.positioner_delay, 0) #if fly scanning, positioner move at speed=step_size/dwell_time, no delay needed  # noqa: E501
    #     else:
    #         yield from bps.mv(self.positioner_delay, dwell_time) #if step scanning, positioners move at 'fast' speed and dwell for specified dwell time at each position.  # noqa: E501

    #     caput(f"{self.pvname}.P1PA", list(arr))
    #     yield from bps.mv(
    #         # self.p1pa,list(arr),
    #         self.positioners.p1.mode, 1,
    #         self.positioners.p1.readback_pv, f"{m1_name}.RBV",
    #         self.positioners.p1.setpoint_pv, f"{m1_name}",
    #         self.number_points, len(arr),
    #     )

    # def setup_scan2(self, m2_name, arr, trigger1="", trigger2="", trigger3="", trigger4=""):  # noqa: E501
    #     print("in setup_scan function")
    #     self.wait_for_connection()

    #     yield from run_blocking_function(self.reset)
    #     yield from bps.sleep(0.2)  # arbitrary wait for EPICS to finish the reset.
    #     caput(f"{self.pvname}.P1PA", list(arr))
    #     yield from bps.mv(
    #         self.positioners.p1.mode, 1,
    #         self.positioners.p1.readback_pv, f"{m2_name}.RBV",
    #         self.positioners.p1.setpoint_pv, f"{m2_name}",
    #         self.number_points, len(arr),
    #         self.triggers.t1.trigger_pv, trigger1,
    #         self.triggers.t2.trigger_pv, trigger2,
    #         self.triggers.t3.trigger_pv, trigger3,
    #         self.triggers.t4.trigger_pv, trigger4,
    #     )


# scan1_pv = iconfig.get("DEVICES")["SCAN1"]
# scan2_pv = iconfig.get("DEVICES")["SCAN2"]
# scan1 = myScanRecord(scan1_pv)
# scan2 = myScanRecord(scan2_pv)
# # scan1 = myScanRecord(scan1_pv, name="scan1")
# # scan2 = myScanRecord(scan2_pv, name="scan2")

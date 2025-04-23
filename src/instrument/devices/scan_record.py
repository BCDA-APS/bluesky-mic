# -*- coding: utf-8 -*-
"""
Created on Oct 16 2024

@author: yluo (grace227)
"""


from apstools.synApps import SscanRecord
from ophyd import EpicsSignal, Component
from epics import PV
from ..devices.utils import mode_setter, value_setter
import bluesky.plan_stubs as bps
import logging


logger = logging.getLogger(__name__)
logger.info(__file__)


class ScanRecord(SscanRecord):
    scan_mode = Component(EpicsSignal, ".P1SM")
    pos_drive = Component(EpicsSignal, ".P1PV")
    pos_readback = Component(EpicsSignal, ".R1PV")
    scan_movement = Component(EpicsSignal, ".P1AR")
    center = Component(EpicsSignal, ".P1CP")
    stepsize = Component(EpicsSignal, ".P1SI")
    width = Component(EpicsSignal, ".P1WD")
    number_points_rbv = Component(EpicsSignal, ".CPT")
    start_position = Component(EpicsSignal, ".P1SP")

    detTrigger_1 = Component(EpicsSignal, ".T1PV")
    detTrigger_2 = Component(EpicsSignal, ".T2PV")
    detTrigger_3 = Component(EpicsSignal, ".T3PV")
    detTrigger_4 = Component(EpicsSignal, ".T4PV")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.P1PA = PV(f"{self.prefix}.P1PA")

    def set_center_width_stepsize(self, center: float, width: float, ss: float):
        """Set center, width, and stepsize in a single motion command."""
        try:
            # yield from bps.mv(self.center, center, self.width, width, self.stepsize, ss)
            yield from bps.mv(self.center, center)
            yield from bps.mv(self.width, width)
            yield from bps.mv(self.stepsize, ss)
            logger.info(
                f"Set center to {center}, width to {width}, and stepsize to {ss} in {self.prefix}."
            )
        except Exception as e:
            logger.error(
                f"Error setting center, width, and stepsize in {self.prefix}: {e}"
            )

    def set_detTriggers(self, trigger_pvs):
        """
        Set detector triggers for the scan record.
        """
        trigger_list = [
            self.detTrigger_1,
            self.detTrigger_2,
            self.detTrigger_3,
            self.detTrigger_4,
        ]
        for detTri, pv_name in zip(trigger_list, trigger_pvs):
            yield from bps.mv(detTri, pv_name)
            logger.info(f"Set {detTri.pvname} to {pv_name} in {self.prefix}.")

    @mode_setter("scan_mode")
    def set_scan_mode(self, mode):
        pass

    @mode_setter("scan_movement")
    def set_rel_abs_motion(self, mode):
        pass

    @value_setter("center")
    def set_center(self, value):
        pass

    @value_setter("width")
    def set_width(self, width):
        pass

    @value_setter("stepsize")
    def set_stepsize(self, stepsize):
        pass

    @value_setter("number_points")
    def set_numpts(self, numpts):
        pass

    @value_setter("pos_drive")
    def set_positioner_drive(self, positioner_pv):
        pass

    @value_setter("pos_readback")
    def set_positioner_readback(self, positioner_rbv):
        pass

    @value_setter("bspv")
    def set_bspv(self, beforescan_pv):
        pass

    @value_setter("aspv")
    def set_aspv(self, afterscan_pv):
        pass

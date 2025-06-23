# -*- coding: utf-8 -*-
"""
Created on Oct 16 2024

@author: yluo (grace227)
"""

import logging

import bluesky.plan_stubs as bps
from apstools.synApps import SscanRecord
from epics import PV
from ophyd import Component
from ophyd import EpicsSignal

from ..devices.utils import mode_setter
from ..devices.utils import value_setter

logger = logging.getLogger(__name__)
logger.info(__file__)


class ScanRecord(SscanRecord):
    """EPICS SscanRecord device with additional scan and trigger utilities."""

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

    detTrigger_1_old = ""
    detTrigger_2_old = ""
    detTrigger_3_old = ""
    detTrigger_4_old = ""

    def __init__(self, *args, **kwargs):
        """Initialize ScanRecord and save current detector triggers."""
        super().__init__(*args, **kwargs)
        self.P1PA = PV(f"{self.prefix}.P1PA")
        self.save_current_detTriggers()

    def set_center_width_stepsize(self, center: float, width: float, ss: float):
        """Set center, width, and stepsize in a single motion command."""
        try:
            yield from bps.mv(self.center, center, self.width, width, self.stepsize, ss)
            logger.info(
                f"Set center to {center}, width to {width}, and stepsize to {ss} in {self.prefix}."
            )
        except Exception as e:
            logger.error(
                f"Error setting center, width, and stepsize in {self.prefix}: {e}"
            )

    def set_detTriggers(self, trigger_pvs):
        """Set detector triggers for the scan record."""
        # Save the current detector triggers before setting new ones
        self.save_current_detTriggers()

        # Set the new detector triggers
        trigger_list = [
            self.detTrigger_1,
            self.detTrigger_2,
            self.detTrigger_3,
            self.detTrigger_4,
        ]
        for detTri, pv_name in zip(trigger_list, trigger_pvs, strict=False):
            yield from bps.mv(detTri, pv_name)
            logger.info(f"Set {detTri.pvname} to {pv_name} in {self.prefix}.")

    def save_current_detTriggers(self):
        """Save the current detector trigger values."""
        self.detTrigger_1_old = self.detTrigger_1.get()
        self.detTrigger_2_old = self.detTrigger_2.get()
        self.detTrigger_3_old = self.detTrigger_3.get()
        self.detTrigger_4_old = self.detTrigger_4.get()

    def restore_detTriggers(self):
        """Restore the detector triggers to the previous values."""
        yield from bps.mv(
            self.detTrigger_1,
            self.detTrigger_1_old,
            self.detTrigger_2,
            self.detTrigger_2_old,
            self.detTrigger_3,
            self.detTrigger_3_old,
            self.detTrigger_4,
            self.detTrigger_4_old,
        )

    @mode_setter("scan_mode")
    def set_scan_mode(self, mode):
        """Set the scan mode for the scan record."""
        pass

    @mode_setter("scan_movement")
    def set_rel_abs_motion(self, mode):
        """Set the scan movement mode (relative or absolute)."""
        pass

    @value_setter("center")
    def set_center(self, value):
        """Set the center value for the scan."""
        pass

    @value_setter("width")
    def set_width(self, width):
        """Set the width value for the scan."""
        pass

    @value_setter("stepsize")
    def set_stepsize(self, stepsize):
        """Set the stepsize value for the scan."""
        pass

    @value_setter("number_points")
    def set_numpts(self, numpts):
        """Set the number of points for the scan."""
        pass

    @value_setter("pos_drive")
    def set_positioner_drive(self, positioner_pv):
        """Set the positioner drive PV for the scan."""
        pass

    @value_setter("pos_readback")
    def set_positioner_readback(self, positioner_rbv):
        """Set the positioner readback PV for the scan."""
        pass

    @value_setter("bspv")
    def set_bspv(self, beforescan_pv):
        """Set the before-scan PV for the scan record."""
        pass

    @value_setter("aspv")
    def set_aspv(self, afterscan_pv):
        """Set the after-scan PV for the scan record."""
        pass

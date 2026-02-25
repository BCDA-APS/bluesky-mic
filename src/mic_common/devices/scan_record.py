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

from mic_common.utils.device_utils import mode_setter
from mic_common.utils.device_utils import value_setter
from mic_common.utils.device_utils import LoggingStageSigs
from mic_common.utils.device_utils import unstage_with_skip

logger = logging.getLogger(__name__)
logger.info(__file__)


class NewScanRecord(SscanRecord):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.P1PA = PV(f"{self.prefix}.P1PA")
        self.P2PA = PV(f"{self.prefix}.P2PA")
        # Wrap stage_sigs with LoggingDict to log all assignments
        original_stage_sigs = self.stage_sigs
        self.stage_sigs = LoggingStageSigs(original_stage_sigs, prefix=self.prefix)

    def stage_detTriggers(self, trigger_pvs):
        """Stage detector triggers for the scan record."""
        for i, t_pv in enumerate(trigger_pvs):
            self.stage_sigs[f"triggers.t{i+1}.trigger_pv"] = t_pv

    def stage_detValues(self, trigger_values):
        """Stage detector values for the scan record."""
        for i, t_value in enumerate(trigger_values):
            self.stage_sigs[f"triggers.t{i+1}.trigger_value"] = t_value

    def config(
        self,
        positioner_setpoint: str,
        positioner_readback: str = "",
        scanmode: int = 0,  # 0: "LINEAR", 1: "TABLE", 2: "FLY"
        rel_abs_motion: int = 0,  # 0: "ABSOLUTE", 1: "RELATIVE"
        center: float = None,
        width: float = 0,
        stepsize: float = 0,
        bspv: str = None,
        aspv: str = None,
        num_points: int = None,
        trigger_pvs: list = None,
        trigger_values: list = None,
        detector_delay: float = None,
    ):
        """Stage the corresponding signals for scanrecord configuration

        Parameters:
        positioner_setpoint: positioner PV string (to get setpoint pv: motor.user_setpoint.pvname)
        positioner_readback: positioner readback PVstring (to get readback pv: motor.user_readback.pvname)
        scanmode: any of the following: LINEAR, FLY, STEP
        rel_abs_motion: any of the following: RELATIVE, ABSOLUTE
        center: float center position
        width: float width of the scan
        stepsize: float stepsize of the scan
        bspv: PV string before scan PV
        aspv: PV string after scan PV
        num_points: int number of points in the scan
        trigger_pvs: list of PV strings of detector trigger PVs

        """
        if self.connected:
            self.stage_sigs.clear()
            self.stage_sigs["positioners.p1.setpoint_pv"] = positioner_setpoint
            self.stage_sigs["positioners.p1.readback_pv"] = positioner_readback
            self.stage_sigs["positioners.p1.mode"] = scanmode
            self.stage_sigs["positioners.p1.abs_rel"] = rel_abs_motion
            self.stage_sigs["positioners.p1.center"] = center
            self.stage_sigs["positioners.p1.width"] = width
            self.stage_sigs["positioners.p1.step_size"] = stepsize

            if aspv is not None:
                self.stage_sigs["aspv"] = aspv

            if bspv is not None:
                self.stage_sigs["bspv"] = bspv

            if num_points is not None:
                self.stage_sigs["number_points"] = num_points
                
            if trigger_pvs is not None:
                self.stage_detTriggers(trigger_pvs)

            if trigger_values is not None:
                self.stage_detValues(trigger_values)

            if detector_delay is not None:
                self.stage_sigs["detector_delay"] = detector_delay

        else:
            logger.error(f"Scan record {self.prefix} is not connected")

    def unstage(self):
        """Unstage the device but avoid restoring file_path and file_name from stage_sigs.

        Uses the unstage_with_skip utility to prevent certain fields from being
        restored during unstage.
        """
        fields_to_skip = ["positioners.p1.step_size"]
        unstage_with_skip(self, fields_to_skip)
        return super().unstage()


class ScanRecord(SscanRecord):
    scan_mode = Component(EpicsSignal, ".P1SM")
    pos_drive = Component(EpicsSignal, ".P1PV")
    pos_readback = Component(EpicsSignal, ".R1PV")
    scan_movement = Component(EpicsSignal, ".P1AR")
    center = Component(EpicsSignal, ".P1CP")
    stepsize = Component(EpicsSignal, ".P1SI")
    width = Component(EpicsSignal, ".P1WD")
    # number_points_rbv = Component(EpicsSignal, ".CPT")
    start_position = Component(EpicsSignal, ".P1SP")
    end_position = Component(EpicsSignal, ".P1EP")

    detTrigger_1_old = ''
    detTrigger_2_old = ''
    detTrigger_3_old = ''
    detTrigger_4_old = ''
    bspv_old = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.P1PA = PV(f"{self.prefix}.P1PA")
        self.P2PA = PV(f"{self.prefix}.P2PA")

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
            logger.error(f"Error setting center, width, and stepsize in {self.prefix}: {e}")

    def set_detTriggers(self, trigger_pvs):
        """
        Set detector triggers for the scan record.
        """
        trigger_list = [
            self.triggers.t1.trigger_pv,
            self.triggers.t2.trigger_pv,
            self.triggers.t3.trigger_pv,
            self.triggers.t4.trigger_pv,
        ]
        self.clear_detTriggers()
        for detTri, pv_name in zip(trigger_list, trigger_pvs, strict=False):
            detTri.put(pv_name)
            yield from bps.sleep(0.1)
            logger.info(f"Set {detTri.pvname} to {pv_name} in {self.prefix}.")

    def save_current_detTriggers(self):
        self.detTrigger_1_old = self.triggers.t1.trigger_pv.get()
        self.detTrigger_2_old = self.triggers.t2.trigger_pv.get()
        self.detTrigger_3_old = self.triggers.t3.trigger_pv.get()
        self.detTrigger_4_old = self.triggers.t4.trigger_pv.get()

    def save_bspv(self):
        self.bspv_old = self.bspv.get()

    def restore_bspv(self):
        self.bspv.put(self.bspv_old)

    def restore_detTriggers(self):
        """
        Restore the detector triggers to the previous values.
        This function assumes that the old values are saved
        """
        self.triggers.t1.trigger_pv.put(self.detTrigger_1_old)
        yield from bps.sleep(0.1)
        self.triggers.t2.trigger_pv.put(self.detTrigger_2_old)
        yield from bps.sleep(0.1)
        self.triggers.t3.trigger_pv.put(self.detTrigger_3_old)
        yield from bps.sleep(0.1)
        self.triggers.t4.trigger_pv.put(self.detTrigger_4_old)
        yield from bps.sleep(0.1)

    def clear_detTriggers(self):
        """
        Clear the detector triggers.
        """
        self.triggers.t1.trigger_pv.put("")
        self.triggers.t2.trigger_pv.put("")
        self.triggers.t3.trigger_pv.put("")
        self.triggers.t4.trigger_pv.put("")
    
    
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

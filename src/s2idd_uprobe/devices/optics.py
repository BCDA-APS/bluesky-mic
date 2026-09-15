"""Optics device module for Bluesky workflows.

This module provides classes for controlling beamline optics devices.
"""

from mic_common.utils.device_utils import mode_setter
from mic_common.utils.device_utils import value_setter
from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal, EpicsSignalRO
from bnp.devices.deltaTau import DeltaTauPiezoBase
from s2idd_uprobe.devices.motor import Motor
import logging

logger = logging.getLogger(__name__)    


class KohzuMono(DeltaTauPiezoBase):
    """
    KohzuMono device for controlling monochromator energy and mode in Bluesky workflows.

    This class extends ophyd.Device and provides
    methods for controlling energy, mode, and related PVs for the id2_d instrument.
    """

    user_setpoint = Component(EpicsSignal, "BraggEAO.VAL")
    user_readback = Component(EpicsSignalRO, "BraggERdbkAO")
    setpoint = Component(EpicsSignal, "BraggEAO.VAL")
    readback = Component(EpicsSignalRO, "BraggERdbkAO")
    mode = Component(EpicsSignal, "KohzuModeBO")
    done = Component(EpicsSignalRO, "KohzuMoving")
    speed_control = Component(EpicsSignal, "KohzuSpeedCtrl")
    POLL_DT = 0.3         # seconds between done checks
    tolerance = 0.0003
    

    def _is_done(self):
        # Example: require both tolerance and hardware done signal
        pos_done = abs(self.setpoint.get() - self.readback.get()) <= self.tolerance
        logger.debug(f"pos_done: {pos_done}, setpoint: {self.setpoint.get()}, readback: {self.readback.get()}")
        return pos_done

    def enable_speed_control(self):
        """Enable the speed control for the monochromator."""
        yield from bps.mv(self.speed_control, 1)
    
    def disable_speed_control(self):
        """Disable the speed control for the monochromator."""
        yield from bps.mv(self.speed_control, 0)
    
    def set_auto_mode(self):
        """Set the mode for the monochromator."""
        yield from bps.mv(self.mode, 1)
    
    def set_manual_mode(self):
        """Set the mode for the monochromator."""
        yield from bps.mv(self.mode, 0)

    @value_setter("mode")
    def set_mode(mode: str) -> None:
        """Set the mode for the monochromator."""
        pass


class OSA(Device):
    """OSA device for controlling the OSA motor in Bluesky workflows."""

    x = Component(Motor, ":m11", kind="config", labels=("motor", "osax"))
    y = Component(Motor, ":m12", kind="config", labels=("motor", "osay"))
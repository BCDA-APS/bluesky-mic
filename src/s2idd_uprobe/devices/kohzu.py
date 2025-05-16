"""KohzuMono device module for Bluesky workflows.

This module provides the KohzuMono class for controlling monochromator energy and mode.
"""

from mic_common.utils.device_utils import mode_setter
from mic_common.utils.device_utils import value_setter
from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal


class KohzuMono(Device):
    """
    KohzuMono device for controlling monochromator energy and mode in Bluesky workflows.

    This module defines the KohzuMono class, which extends ophyd.Device and provides
    methods for controlling energy, mode, and related PVs for the id2_d instrument.
    """

    energy = Component(EpicsSignal, "BraggEAO")
    energy_rbv = Component(EpicsSignal, "BraggERdbkAO")
    mode = Component(EpicsSignal, "KohzuModeBO")
    mode2 = Component(EpicsSignal, "KohzuMode2MO")
    move = Component(EpicsSignal, "KohzuPutBO")
    moving = Component(EpicsSignal, "KohzuMoving")

    @value_setter("energy")
    def set_energy(energy: float) -> None:
        """Set the energy value for the monochromator."""
        pass

    @value_setter("move")
    def set_move(move: float) -> None:
        """Set the move command for the monochromator."""
        pass

    @mode_setter("mode")
    def set_mode(mode: str) -> None:
        """Set the mode for the monochromator."""
        pass

    @mode_setter("mode2")
    def set_mode2(mode2: str) -> None:
        """Set the secondary mode for the monochromator."""
        pass

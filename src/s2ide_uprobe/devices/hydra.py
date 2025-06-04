"""Hydra device module."""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal
from mic_common.utils.device_utils import value_setter, mode_setter

class Hydra(Device):
    """Hydra device."""

    delay_us = Component(EpicsSignal, ":Delay")
    width_us = Component(EpicsSignal, ":Width")
    polarity = Component(EpicsSignal, ":Polarity")
    mode = Component(EpicsSignal, ":Mode")
    start_position = Component(EpicsSignal, ":StartPosition")
    end_position = Component(EpicsSignal, ":EndPosition")
    total_trigger = Component(EpicsSignal, ":NumTriggers")
    send_parameters = Component(EpicsSignal, ":StartStopCalc.PROC")

    @value_setter("delay_us")
    def set_delay_us(self, delay_us):
        """Set the delay in microseconds."""
        self.delay_us.put(delay_us)

    @value_setter("width_us")
    def set_width_us(self, width_us):
        """Set the width in microseconds."""
        self.width_us.put(width_us)

    @value_setter("start_position")
    def set_start_position(self, start_position):
        """Set the start position."""
        self.start_position.put(start_position)

    @value_setter("end_position")
    def set_end_position(self, end_position):
        """Set the end position."""
        self.end_position.put(end_position)

    @value_setter("total_trigger")
    def set_total_trigger(self, total_trigger):
        """Set the total trigger."""
        self.total_trigger.put(total_trigger)

    @value_setter("send_parameters")
    def set_send_parameters(self, send_parameters):
        """Set the send parameters."""
        self.send_parameters.put(send_parameters)

    @mode_setter("mode")
    def set_mode(self, mode):
        """Set the mode."""
        self.mode.put(mode)

    @mode_setter("polarity")
    def set_polarity(self, polarity):
        """Set the polarity."""
        self.polarity.put(polarity)

    
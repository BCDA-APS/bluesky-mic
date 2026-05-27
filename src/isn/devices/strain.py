from ophyd import Device, EpicsSignalRO
from ophyd import Component
from ophyd import EpicsSignal
from ophyd import Signal

import time
import logging
from ophyd import PVPositionerIsClose

from ophyd.status import Status, SubscriptionStatus

logger = logging.getLogger(__name__)




class VoltagePositioner(PVPositionerIsClose):
    setpoint = Component(EpicsSignal, '.A')
    readback = Component(EpicsSignal, '.A')

    atol = 0.5  # absolute tolerance
    rtol = 0

    

class RP100(Device):
    """Razorbill RP100 power supply."""

    _default_configuration_attrs = ['voltage_1', 'voltage_2']

    enable_1 = Component(EpicsSignal, 'wOutput1_Enabled', name='Enable 1')
    enable_2 = Component(EpicsSignal, 'wOutput2_Enabled', name='Enable 2')
    voltage_1 = Component(VoltagePositioner, 'VoltageLimit1', name='Voltage 1')
    voltage_2 = Component(VoltagePositioner, 'VoltageLimit2', name='Voltage 2')
    slew_rate_1 = Component(EpicsSignal, 'wOutput1_Slew', name='Slew Rate 1')
    slew_rate_2 = Component(EpicsSignal, 'wOutput2_Slew', name='Slew Rate 2')


class MP240(Device):
    """Razorbill MP240 Multiplexer."""
    _default_configuration_attrs = ['channel']
    channel = Component(EpicsSignal, 'MP240:channel.VAL', name='Channel')


class LCRMeter(Device):
    """Keysight LCR Meter."""
    _default_read_attrs = ['capacitance']
    capacitance = Component(EpicsSignalRO, 'E4980:1:val1_RBV', name='Capacitance')


class CombinedCapSensorReading(Device):

    mp240 = Component(MP240, '', name='mux')
    lcr = Component(LCRMeter, '', name='lcr')





# Argo's dumb attempt

class DualCapacitanceSensor(Device):
    """
    Bluesky device that reads two independent capacitance values
    by switching a multiplexer between two channels and reading
    an LCR meter after each switch.
    """

    # Internal sub-devices
    mux = Component(MP240, '', name='mux')
    lcr = Component(LCRMeter, '', name='lcr')

    # Stored readings as internal signals
    capacitance_1 = Component(Signal, name='capacitance_1', kind='hinted', value=0.0)
    capacitance_2 = Component(Signal, name='capacitance_2', kind='hinted', value=0.0)

    def __init__(self, prefix, *args,
                 mux_channel_1=1, mux_channel_2=2,
                 settle_time=0.5, **kwargs):
        super().__init__(prefix, *args, **kwargs)
        self._mux_channel_1 = mux_channel_1
        self._mux_channel_2 = mux_channel_2
        self._settle_time = settle_time

    def _switch_and_read(self, mux_channel):
        """
        Switch the multiplexer to the given channel, wait for settling,
        and return the current LCR capacitance reading.
        """
        # Set the mux channel and wait for completion
        st = self.mux.channel.set(mux_channel)
        st.wait(timeout=5.0)

        # Wait for signal to settle after relay switching
        time.sleep(self._settle_time)

        # Read the capacitance
        capacitance_value = self.lcr.capacitance.get()
        return capacitance_value

    def trigger(self):
        """
        Trigger sequential measurements on both channels.
        Switches mux → reads LCR → switches mux → reads LCR.
        """
        status = Status()

        def measure():
            try:
                # Measure channel 1
                cap1 = self._switch_and_read(self._mux_channel_1)
                self.capacitance_1.put(cap1)
                logger.info(
                    f"Channel {self._mux_channel_1}: capacitance = {cap1}"
                )

                # Measure channel 2
                cap2 = self._switch_and_read(self._mux_channel_2)
                self.capacitance_2.put(cap2)
                logger.info(
                    f"Channel {self._mux_channel_2}: capacitance = {cap2}"
                )

                status.set_finished()
            except Exception as exc:
                logger.error(f"Measurement failed: {exc}")
                status.set_exception(exc)

        # Run in a background thread to avoid blocking the RunEngine
        import threading
        thread = threading.Thread(target=measure, daemon=True)
        thread.start()

        return status

    def read(self):
        """Return the most recently triggered readings."""
        return {
            self.capacitance_1.name: {
                'value': self.capacitance_1.get(),
                'timestamp': time.time(),
            },
            self.capacitance_2.name: {
                'value': self.capacitance_2.get(),
                'timestamp': time.time(),
            },
        }

    def describe(self):
        return {
            self.capacitance_1.name: {
                'source': f'MUX ch{self._mux_channel_1} -> LCR',
                'dtype': 'number',
                'shape': [],
                'units': 'F',
            },
            self.capacitance_2.name: {
                'source': f'MUX ch{self._mux_channel_2} -> LCR',
                'dtype': 'number',
                'shape': [],
                'units': 'F',
            },
        }

    @property
    def hints(self):
        return {'fields': [self.capacitance_1.name, self.capacitance_2.name]}
"""Sensor devices used by the 2IDD automatic optimization workflows."""

import threading

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd.status import DeviceStatus

import logging


logger = logging.getLogger(__name__)


class JoergerScaler(Device):
    """Triggerable Joerger scaler for step scans and Blop optimization.

    The Joerger scaler is configured for one-shot mode by writing ``0`` to
    ``scaler1.CONT`` and started by writing ``1`` to ``scaler1.CNT``.  It
    does not expose a completion PV in this device, so ``trigger()`` returns a
    status which completes after the configured preset time.  This makes the
    device usable as a Bluesky detector: ``trigger_and_read`` will not read
    USIC/DSIC until the new count is expected to be available.

    The timing assumption should be checked against the IOC configuration. If
    a reliable scaler-done PV is available later, it should replace the timer
    in ``trigger()``.
    """

    # ``count_mode`` is retained as a configuration signal.  The old public
    # name ``coumt_mode`` was misspelled; keep it as an alias below for
    # compatibility with any existing plans.
    count_mode = Component(EpicsSignal, ":scaler1.CONT", kind="config", labels=("scaler", "count_mode"))
    count_time = Component(EpicsSignal, ":scaler1.TP", kind="config", labels=("scaler", "count_time"))
    count_trigger = Component(EpicsSignal, ":scaler1.CNT", kind="omitted", labels=("scaler", "trigger"))
    counts = Component(EpicsSignalRO, ":scaler1.CNT", kind="normal", labels=("scaler", "counts"))
    usic_counts = Component(
        EpicsSignalRO,
        ":scaler1_cts1.C",
        kind="normal",
        labels=("scaler", "upstream_counts"),
    )
    dsic_counts = Component(
        EpicsSignalRO,
        ":scaler1_cts1.B",
        kind="normal",
        labels=("scaler", "downstream_counts"),
    )

    # Small margin for EPICS processing and PV propagation after the preset
    # interval expires.  This can be adjusted without changing the PV map.
    trigger_settle_time = 0.05

    @property
    def coumt_mode(self):
        """Backward-compatible alias for the formerly misspelled signal."""
        return self.count_mode

    def trigger(self):
        """Start one scaler acquisition and finish after its preset time."""
        status = DeviceStatus(self)

        try:
            preset_time = max(0.0, float(self.count_time.get()))
            # Always select one-shot mode before triggering.  Mode 0 is
            # one-shot; mode 1 is continuous/autocount on this scaler IOC.
            self.count_mode.put(0, wait=True)
            # A blocking put confirms that the IOC accepted the trigger before
            # the status timer starts.
            self.count_trigger.put(1, wait=True)
        except Exception as exc:
            status.set_exception(exc)
            return status

        timer = threading.Timer(
            preset_time + self.trigger_settle_time,
            status.set_finished,
        )
        timer.daemon = True
        timer.start()
        return status



class SR570(Device):
    """SR570 current for controlling the SR570 in Bluesky workflows."""

    gain_value = Component(EpicsSignal, "sens_num.VAL", kind="config", labels=("sr570", "gain_value"))
    gain_unit = Component(EpicsSignal, "sens_unit.VAL", kind="config", labels=("sr570", "gain_unit"))
    gain_mode = Component(EpicsSignal, "gain_mode.VAL", kind="config", labels=("sr570", "gain_mode"))
    invert_mode = Component(EpicsSignal, "invert_on.VAL", kind="config", labels=("sr570", "invert_mode_on"))
    bias_mode = Component(EpicsSignal, "bias_on.VAL", kind="config", labels=("sr570", "bias_mode_on"))

    def preset_config(self):
        """Preset configuration for the SR570 device."""
        self.gain_value.put(5)  # 0: 1; 2: 2; 3: 10; 4: 20; 5: 50; 6: 100; 7: 200; 8: 500; 
        logger.info("SR570 gain value set to 20 (index 4)")
        self.gain_unit.put(1)   # 0: pA/V; 1: nA/V; 2: uA/V; 3: mA/V
        logger.info("SR570 gain unit set to nA/V (index 1)")
        self.gain_mode.put(0)   # 0: low noise; 1: high bw; 2: low drift
        logger.info("SR570 gain mode set to low noise (index 0)")
        self.invert_mode.put(0) # 0: off; 1: on
        logger.info("SR570 invert mode set to off (index 0)")
        self.bias_mode.put(0)   # 0: off; 1: on
        logger.info("SR570 bias mode set to off (index 0)")


class Preamps(Device):
    """Preamps setting for both upstream and downstream SR570 in Bluesky workflows."""

    upstream = Component(SR570, ":A1", kind="config", labels=("sr570", "upstream"))
    downstream = Component(SR570, ":A2", kind="config", labels=("sr570", "downstream"))




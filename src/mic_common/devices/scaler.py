"""SIS3820 scaler device module."""

from ophyd import Component, Device, EpicsSignal
from ophyd.device import Staged
from mic_common.utils.device_utils import LoggingStageSigs
import logging

# from mic_common.utils.device_utils import value_setter, mode_setter

logger = logging.getLogger(__name__)

class SCALER(Device):
    """ scaler device."""
    stop_all = Component(EpicsSignal, ":StopAll")
    time_period = Component(EpicsSignal, ":scaler1.TP")
    count_mode = Component(EpicsSignal, ":scaler1.CONT")
    count = Component(EpicsSignal, ":scaler1.CNT")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        original_stage_sigs = self.stage_sigs
        self.stage_sigs = LoggingStageSigs(original_stage_sigs, prefix=self.prefix)

    def config_stepscan(self, dwell_time=None, **kwargs):
        """Configure for step scan"""
        self.unstage()
        self.stage_sigs.clear()
        self.stage_sigs["stop_all"] = 1
        self.stage_sigs["count_mode"] = 0
        self.stage_sigs["time_period"] = dwell_time

    def unstage(self):
        """Unstage the SIS3820 device."""
        # Check if device is already staged and unstage if necessary
        if self._staged == Staged.yes:
            logger.info("SIS3820 is already staged, unstaging ... ...")
            return super().unstage()

   
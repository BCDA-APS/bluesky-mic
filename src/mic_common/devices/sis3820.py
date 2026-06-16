"""SIS3820 scaler device module."""

from ophyd import Component, Device, EpicsSignal
from ophyd.device import Staged
from mic_common.utils.device_utils import LoggingStageSigs
import logging

# from mic_common.utils.device_utils import value_setter, mode_setter

logger = logging.getLogger(__name__)


class SIS3820(Device):
    """SIS3820 scaler device."""

    num_ch_used = Component(EpicsSignal, ":NuseAll")
    stop_all = Component(EpicsSignal, ":StopAll")
    erase_start = Component(EpicsSignal, ":EraseStart")
    acquiring = Component(EpicsSignal, ":Acquiring")
    current_channel = Component(EpicsSignal, ":CurrentChannel")
    elapsed_real = Component(EpicsSignal, ":ElapsedReal")
    preset_real = Component(EpicsSignal, ":PresetReal")
    prescale = Component(EpicsSignal, ":Prescale")
    trigger_mode = Component(EpicsSignal, ":ChannelAdvance")
    software_trigger = Component(EpicsSignal, ":SoftwareChannelAdvance")
    time_period = Component(EpicsSignal, ":scaler1.TP")
    count_mode = Component(EpicsSignal, ":scaler1.CONT")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        original_stage_sigs = self.stage_sigs
        self.stage_sigs = LoggingStageSigs(original_stage_sigs, prefix=self.prefix)

    def setup_prescale(self, stepsize, motor_resolution):
        """Set prescale based on stepsize and motor resolution"""
        prescale = abs(stepsize / motor_resolution) + 0.0001
        yield from self.set_prescale(int(prescale))

    def calculate_prescale(self, stepsize, motor_resolution):
        """Calculate prescale based on stepsize and motor resolution"""
        prescale = abs(stepsize / motor_resolution) + 0.0001
        return int(prescale)

    def config_flyscan(
        self,
        num_pulses=None,
        update_prescale=True,
        stepsize=None,
        motor_resolution=None,
        trigger_mode="External",
        **kwargs,
    ):
        """Configure for flyscan"""
        self.unstage()
        self.stage_sigs.clear()
        self.stage_sigs["stop_all"] = 1
        self.stage_sigs["num_ch_used"] = num_pulses
        self.stage_sigs["trigger_mode"] = trigger_mode
        self.stage_sigs["preset_real"] = 0
        if update_prescale:
            if stepsize is not None and motor_resolution is not None:
                prescale = self.calculate_prescale(stepsize, motor_resolution)
                self.stage_sigs["prescale"] = prescale
            else:
                raise ValueError("Stepsize and motor resolution must be provided")

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

    def unhang(self, retries: int = 1, delay_s: float = 0.0) -> dict[str, object]:
        """Stop SIS3820 acquisition immediately."""
        del delay_s
        attempts = max(1, int(retries))
        results: list[dict[str, object]] = []
        for attempt in range(1, attempts + 1):
            self.stop_all.put(1)
            results.append({"attempt": attempt, "success": True})
        return {
            "device": self.name,
            "success": True,
            "retries": attempts,
            "attempts": results,
        }

   

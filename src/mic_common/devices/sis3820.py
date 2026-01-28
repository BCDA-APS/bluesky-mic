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
    prescale = Component(EpicsSignal, ":Prescale")
    trigger_mode = Component(EpicsSignal, ":ChannelAdvance")
    software_trigger = Component(EpicsSignal, ":SoftwareChannelAdvance")

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

    # def before_flyscan(self, num_pts, update_prescale=True, stepsize=None, motor_resolution=None):
    #     """Configure scaler before flyscan."""
    #     yield from self.set_stop_all(1)
    #     yield from self.set_num_ch_used(num_pts)
    #     yield from self.set_trigger_mode("External")
    #     if update_prescale:
    #         if stepsize is not None and motor_resolution is not None:
    #             yield from self.setup_prescale(stepsize, motor_resolution)
    #         else:
    #             raise ValueError("Stepsize and motor resolution must be provided")

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
        if update_prescale:
            if stepsize is not None and motor_resolution is not None:
                prescale = self.calculate_prescale(stepsize, motor_resolution)
                self.stage_sigs["prescale"] = prescale
            else:
                raise ValueError("Stepsize and motor resolution must be provided")

    def unstage(self):
        """Unstage the SIS3820 device."""
        # Check if device is already staged and unstage if necessary
        if self._staged == Staged.yes:
            logger.info("SIS3820 is already staged, unstaging ... ...")
            return super().unstage()

    # def before_stepscan(self, num_pts):
    #     """Configure scaler before stepscan."""
    #     yield from self.set_stop_all(1)
    #     yield from self.set_num_ch_used(num_pts)
    #     yield from self.set_trigger_mode("Internal")

    # def set_internal_trigger(self):
    #     """Set internal trigger."""
    #     yield from self.set_trigger_mode("Internal")

    # def set_external_trigger(self):
    #     """Set external trigger."""
    #     yield from self.set_trigger_mode("External")

    # @value_setter("num_ch_used")
    # def set_num_ch_used(num_ch_used):
    #     """Set number of channels used."""
    #     pass

    # @value_setter("stop_all")
    # def set_stop_all(stop_all):
    #     """Set stop all signal."""
    #     pass

    # @value_setter("erase_start")
    # def set_erase_start(erase_start):
    #     """Set erase start signal."""
    #     pass

    # @value_setter("prescale")
    # def set_prescale(prescale):
    #     """Set prescale."""
    #     pass

    # @value_setter("software_trigger")
    # def software_trig(software_trigger):
    #     """Set software trigger."""
    #     pass

    # @mode_setter("trigger_mode")
    # def set_trigger_mode(trigger_mode):
    #     """Set trigger mode."""
    #     pass

    # @mode_setter("software_trigger")
    # def set_software_trigger(software_trigger):
    #     """Set software trigger."""
    #     pass

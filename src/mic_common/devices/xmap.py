"""
Created on Jan 15 2024

4-elm XMAP

@author: yluo (grace227)
"""

# from apstools.devices import Struck3820
from ophyd import Component, Device, EpicsSignal, EpicsSignalRO
from ophyd.device import Staged

from mic_common.utils.device_utils import mode_setter
from mic_common.utils.device_utils import value_setter
from mic_common.utils.device_utils import LoggingStageSigs
from mic_common.devices.ad_fileplugin import DetNetCDF
from mic_common.devices.save_data import SaveDataMic
import numpy as np
import logging

logger = logging.getLogger(__name__)


class XMAPBase(Device):
    """4-element XMAP device for X-ray spectroscopy."""

    start_all = Component(EpicsSignal, ":StartAll")
    stop_all = Component(EpicsSignal, ":StopAll")
    erase_start = Component(EpicsSignal, ":EraseStart")
    erase_all = Component(EpicsSignal, ":EraseAll")
    acquiring = Component(EpicsSignalRO, ":Acquiring", string=True)
    collection_mode = Component(EpicsSignal, ":CollectMode")
    preset_mode = Component(EpicsSignal, ":PresetMode")
    elapsed_real_time = Component(EpicsSignalRO, ":ElapsedReal")
    preset_real_time = Component(EpicsSignal, ":PresetReal")
    elapsed_live_time = Component(EpicsSignalRO, ":ElapsedLive")
    preset_live_time = Component(EpicsSignal, ":PresetLive")
    status_rate = Component(EpicsSignal, ":StatusAll.SCAN")
    read_rate = Component(EpicsSignal, ":ReadAll.SCAN")
    pixels_per_run = Component(EpicsSignal, ":PixelsPerRun")
    buffer_size: int = 124
    num_capture: int = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        original_stage_sigs = self.stage_sigs
        self.stage_sigs = LoggingStageSigs(original_stage_sigs, prefix=self.prefix)

    def calc_num_capture(self, num_pulses: int):
        """Calculate the number of capture based on number of scan points."""
        self.num_capture = int(np.ceil(num_pulses / self.buffer_size))

    # def before_stepscan(self, dwell_ms):
    #     """Initialize XMAP before step scan."""
    #     dwell_sec = dwell_ms / 1000
    #     yield from self.set_stop_all(1)
    #     yield from self.set_collection_mode("MCA SPECTRA")
    #     yield from self.set_preset_mode("Real Time")
    #     yield from self.set_real_time(dwell_sec)
    #     yield from self.set_status_rate("Passive")
    #     yield from self.set_read_rate("Passive")

    # def after_stepscan(self):
    #     """Configure XMAP after step scan."""
    #     yield from self.set_status_rate(".2 SECOND")
    #     yield from self.set_read_rate(".2 SECOND")

    # def before_flyscan(self, num_pts):
    #     """Initialize XMAP before fly scan.

    #     Parameters:
    #         num_pts (int): Number of points to collect.
    #     """
    #     yield from self.set_stop_all(1)
    #     yield from self.set_collection_mode("MCA MAPPING")
    #     yield from self.set_pixels_per_run(num_pts)

    def config_flyscan(self, num_pts):
        """Configure XMAP before fly scan."""
        self.stage_sigs.clear()
        self.stage_sigs["stop_all"] = 1
        self.stage_sigs["collection_mode"] = 1  # "MCA MAPPING"
        self.stage_sigs["pixels_per_run"] = num_pts

    # def flyscan_after(self):
    #     """Configure XMAP after fly scan."""
    #     yield from self.set_collection_mode("MCA SPECTRA")

    # @mode_setter("preset_mode")
    # def set_preset_mode(mode):
    #     """Set preset mode."""
    #     pass

    # @mode_setter("collection_mode")
    # def set_collection_mode(mode):
    #     """Set collection mode."""
    #     pass

    # @mode_setter("status_rate")
    # def set_status_rate(rate):
    #     """Set status update rate."""
    #     pass

    # @mode_setter("read_rate")
    # def set_read_rate(rate):
    #     """Set read rate."""
    #     pass

    # @value_setter("preset_real_time")
    # def set_real_time(real_time):
    #     """Set preset real time."""
    #     pass

    # @value_setter("preset_live_time")
    # def set_live_time(live_time):
    #     """Set preset live time."""
    #     pass

    # @value_setter("pixels_per_run")
    # def set_pixels_per_run(numpts):
    #     """Set number of pixels per run."""
    #     pass

    # @value_setter("stop_all")
    # def set_stop_all(stop_all):
    #     """Set stop all signal."""
    #     pass

    # @value_setter("erase_start")
    # def set_erase_start(erase_start):
    #     """Set erase start signal."""
    #     pass


class XMAP(Device):
    """4-element XMAP device for X-ray spectroscopy."""

    cam = Component(XMAPBase, "", kind="config", labels=("xmap", "cam"))
    fileplugin = Component(DetNetCDF, ":netCDF1:", kind="config", labels=("xmap", "fileplugin"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        original_stage_sigs = self.stage_sigs
        self.stage_sigs = LoggingStageSigs(original_stage_sigs, prefix=self.prefix)

    def config_flyscan(self, num_pulses: int = None, **kwargs):
        """Configure XMAP for fly scan."""
        self.unstage()
        try:
            self.cam.config_flyscan(num_pulses)
            self.cam.calc_num_capture(num_pulses)
        except Exception as e:
            logger.error(f"Error configuring XMAP for fly scan: {e}")
            raise e

        try:
            self.fileplugin.config_file_writer(self.cam.num_capture, **kwargs)
            self.fileplugin.stage_sigs.pop("parent.cam.array_callbacks", None)
        except Exception as e:
            logger.error(f"Error configuring fileplugin for fly scan: {e}")
            raise e

    def unstage(self):
        """Unstage the XMAP device."""
        # Check if device is already staged and unstage if necessary
        if self._staged == Staged.yes:
            logger.info("XMAP is already staged, unstaging ... ...")
            return super().unstage()

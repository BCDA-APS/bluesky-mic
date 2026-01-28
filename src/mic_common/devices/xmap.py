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

    def config_flyscan(self, num_pts):
        """Configure XMAP before fly scan."""
        self.stage_sigs.clear()
        self.stage_sigs["stop_all"] = 1
        self.stage_sigs["collection_mode"] = 1  # "MCA MAPPING"
        self.stage_sigs["pixels_per_run"] = num_pts


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

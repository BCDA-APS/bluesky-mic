# -*- coding: utf-8 -*-
"""
Created on Dec 04 2024

@author: yluo (grace227)
"""
# TODO: Add back the colon

import datetime
import logging
import time

from ophyd import Component, Device, EpicsSignal, EpicsSignalRO
from ophyd.areadetector.cam import Xspress3DetectorCam
from apstools.devices import CamMixin_V34
from mic_common.devices.ad_fileplugin import DetHDF5
from mic_common.utils.device_utils import LoggingStageSigs


logger = logging.getLogger(__name__)
logger.info(__file__)


class Xspress3Base(CamMixin_V34, Xspress3DetectorCam):

    def __init__(self, *args, **kwargs):
        """Initialize Xspress3 detector."""
        super().__init__(*args, **kwargs)
        original_stage_sigs = self.stage_sigs
        self.stage_sigs = LoggingStageSigs(original_stage_sigs, prefix=self.prefix)

    def config(
        self,
        num_pulses: int = None,
        dwell_time: float = None, # unit in seconds
        trigger_mode: int = 3, # 3: "TTL", 1: "Internal"
        **kwargs
        ):

        self.stage_sigs.clear()
        self.stage_sigs['acquire'] = 0
        self.stage_sigs['trigger_mode'] = trigger_mode
        self.stage_sigs['acquire_time'] = dwell_time
        self.stage_sigs['num_images'] = num_pulses

class BNPXspress3(Device):
    """Xspress3 detector camera for BNP."""
    cam = Component(Xspress3Base, ":det1:", kind="config", labels=("xsp3", "cam"))
    fileplugin = Component(DetHDF5, ":HDF1:", kind="config", labels=("xsp3", "fileplugin"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.fileplugin.stage_sigs.pop("parent.cam.array_callbacks", None)
            logger.info("Removing array_callbacks stage signal from XP3 fileplugin")
        except Exception as e:
            logger.error(f"Error removing array_callbacks stage signal from XP3 fileplugin: {e}")
            raise e

    def config_flyscan(self, num_pulses: int = None, dwell_time: float = None, **kwargs):
        """Configure the Eiger2ID device for a flyscan with the given points and dwell time."""
        self.unstage()
        try:
            self.cam.config(num_pulses, dwell_time, **kwargs)
        except Exception as e:
            logger.error(f"Error configuring cam for fly scan: {e}")
            raise e

        try:
            self.fileplugin.config_file_writer(num_pulses, **kwargs)
            self.fileplugin.stage_sigs.pop("parent.cam.array_callbacks", None)
        except Exception as e:
            logger.error(f"Error configuring fileplugin for fly scan: {e}")
            raise e
    
    def unhang(self, retries: int = 1, delay_s: float = 0.1) -> dict[str, object]:
        attempts = max(1, int(retries))
        results: list[dict[str, object]] = []
        for attempt in range(1, attempts + 1):
            try:
                self.cam.acquire.put(0, wait=True)
                self.fileplugin.capture.put(0, wait=True)
                results.append({"attempt": attempt, "success": True})
                if attempt < attempts and delay_s > 0:
                    time.sleep(delay_s)
            except Exception as exc:
                logger.exception("Failed to unhang Xspress3 on attempt %s", attempt)
                results.append({"attempt": attempt, "success": False, "error": str(exc)})
                return {
                    "device": self.name,
                    "success": False,
                    "retries": attempts,
                    "attempts": results,
                }
        return {
            "device": self.name,
            "success": True,
            "retries": attempts,
            "attempts": results,
        }

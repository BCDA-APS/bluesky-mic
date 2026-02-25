# -*- coding: utf-8 -*-
"""
Created on Dec 04 2024

@author: yluo (grace227)
"""
# TODO: Add back the colon

import datetime
import logging

from ophyd.device import Staged
from ophyd import Component, Device, EpicsSignal, EpicsSignalRO
from ophyd.areadetector.cam import Xspress3DetectorCam
from mic_common.devices.ad_fileplugin import DetHDF5
from mic_common.utils.device_utils import LoggingStageSigs


logger = logging.getLogger(__name__)
logger.info(__file__)


class s8bmbXspress3Base(Device):

    acquire = Component(EpicsSignal, "Acquire")
    trigger_mode = Component(EpicsSignal, "TriggerMode")
    num_images = Component(EpicsSignal, "NumImages")
    acquire_time = Component(EpicsSignal, "AcquireTime")
    soft_trigger = Component(EpicsSignal, "SoftTrigger")
    array_size: int = 4096

    def __init__(self, *args, **kwargs):
        """Initialize Xspress3 detector."""
        super().__init__(*args, **kwargs)
        original_stage_sigs = self.stage_sigs
        self.stage_sigs = LoggingStageSigs(original_stage_sigs, prefix=self.prefix)

    def config(self):
        """Configure Xspress3 detector."""
        pass

class Xspress3(Device):
    """Xspress3 detector camera for BNP."""
    cam = Component(s8bmbXspress3Base, ":det1:", kind="config", labels=("xsp3", "cam"))
    fileplugin = Component(DetHDF5, ":HDF1:", kind="config", labels=("xsp3", "fileplugin"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.fileplugin.stage_sigs.pop("parent.cam.array_callbacks", None)
            logger.info("Removing array_callbacks stage signal from Xspress3 fileplugin")
        except Exception as e:
            logger.error(f"Error removing array_callbacks stage signal from Xspress3 fileplugin: {e}")
            raise e

    def config_flyscan(self, num_pulses: int = None, dwell_time: float = None, **kwargs):
        self.unstage()
        try:
            # Lets stage the det1 
            self.cam.stage_sigs.clear()
            self.cam.stage_sigs["acquire"] = 0
            self.cam.stage_sigs["trigger_mode"] = 3 # 3: TTL Veto only, 7: Software+Internal
            self.cam.stage_sigs["num_images"] = num_pulses
            self.cam.stage_sigs['acquire_time'] = dwell_time / 1000

            self.fileplugin.config_file_writer(num_pulses, upper_det_foldername=False, **kwargs)
            self.fileplugin.stage_sigs.pop("parent.cam.array_callbacks", None)
        except Exception as e:
            logger.error(f"Error configuring fileplugin for fly scan: {e}")
            raise e

    def config_stepscan(self, num_pulses: int = None, dwell_time: float = None, **kwargs):
        self.unstage()
        try:
            # Lets stage the det1 
            self.cam.stage_sigs.clear()
            self.cam.stage_sigs["acquire"] = 0
            self.cam.stage_sigs["trigger_mode"] = 7 # 3: TTL Veto only, 1: Internal, 7: Software+Internal
            self.cam.stage_sigs["num_images"] = num_pulses
            self.cam.stage_sigs['acquire_time'] = dwell_time
            
            self.fileplugin.config_file_writer(num_pulses, upper_det_foldername=False, **kwargs)
            self.fileplugin.stage_sigs.pop("parent.cam.array_callbacks", None)
        except Exception as e:
            logger.error(f"Error configuring fileplugin for step scan: {e}")
            raise e


    def unstage(self):
        """Unstage the Xspress3 device."""
        # Check if device is already staged and unstage if necessary
        if self._staged == Staged.yes:
            logger.info("Xspress3 is unstaged, unstaging ... ...")
            return super().unstage()
        elif self._staged == Staged.partially:
            logger.info("Xspress3 is partially staged, unstaging cam and fileplugin separately...")
            if self.cam._staged == Staged.yes or self.cam._staged == Staged.partially:
                self.cam.unstage()
            if self.fileplugin._staged == Staged.yes or self.fileplugin._staged == Staged.partially:
                self.fileplugin.unstage()
            return super().unstage()
    

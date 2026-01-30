# -*- coding: utf-8 -*-
"""
Created on Dec 04 2024

@author: yluo (grace227)
"""
# TODO: Add back the colon

import datetime
import logging

from ophyd import Component, Device, EpicsSignal, EpicsSignalRO
from ophyd.areadetector.cam import Xspress3DetectorCam
from mic_common.devices.ad_fileplugin import DetHDF5
from mic_common.utils.device_utils import LoggingStageSigs


logger = logging.getLogger(__name__)
logger.info(__file__)


# class Xspress3Base(Xspress3DetectorCam):

#     def __init__(self, *args, **kwargs):
#         """Initialize Xspress3 detector."""
#         super().__init__(*args, **kwargs)
#         original_stage_sigs = self.stage_sigs
#         self.stage_sigs = LoggingStageSigs(original_stage_sigs, prefix=self.prefix)

#     def config(self):
#         """Configure Xspress3 detector."""
#         pass

class Xspress3(Device):
    """Xspress3 detector camera for BNP."""
    cam = Component(Xspress3DetectorCam, ":det1:", kind="config", labels=("xsp3", "cam"))
    fileplugin = Component(DetHDF5, ":HDF1:", kind="config", labels=("xsp3", "fileplugin"))
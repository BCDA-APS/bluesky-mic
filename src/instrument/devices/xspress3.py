# -*- coding: utf-8 -*-
"""
Created on Dec 04 2024

@author: yluo (grace227)
"""

from ..utils.config_loaders import iconfig

# from ophyd import Device, EpicsSignal, Component
from ophyd.areadetector.cam import Xspress3DetectorCam
from ..devices.utils import mode_setter, value_setter
import bluesky.plan_stubs as bps
import logging
import os

logger = logging.getLogger(__name__)
logger.info(__file__)


class Xspress3(Xspress3DetectorCam):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

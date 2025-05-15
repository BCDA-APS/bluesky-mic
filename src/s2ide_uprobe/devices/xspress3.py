# -*- coding: utf-8 -*-
"""
Created on Dec 04 2024

@author: yluo (grace227)
"""

import logging

from ophyd import Component
from ophyd import EpicsSignal
from ophyd.areadetector.cam import Xspress3DetectorCam

from ..devices.utils import mode_setter
from ..devices.utils import value_setter

logger = logging.getLogger(__name__)
logger.info(__file__)


class Xspress3(Xspress3DetectorCam):
    erase_on_start = Component(EpicsSignal, "EraseOnStart")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def scan_init(self, exposure_time=0, num_images=0):
        yield from self.set_acquire_time(exposure_time)
        yield from self.set_num_images(num_images)

    @mode_setter("image_mode")
    def set_image_mode(mode):
        pass

    @mode_setter("erase_on_start")
    def set_erase_on_start(mode):
        pass

    @mode_setter("trigger_mode")
    def set_trigger_mode(mode):
        pass

    @value_setter("acquire_time")
    def set_acquire_time(exposure_time):
        pass

    @value_setter("num_images")
    def set_num_images(num_images):
        pass

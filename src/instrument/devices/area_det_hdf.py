# -*- coding: utf-8 -*-
"""
Created on Dec 03 2024

@author: yluo (grace227)
"""

from ophyd.areadetector.plugins import HDF5Plugin
from ..devices.utils import mode_setter, value_setter
import os

# import bluesky.plan_stubs as bps
# from functools import wraps
import logging


logger = logging.getLogger(__name__)
logger.info(__file__)


class DetHDF5(HDF5Plugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _validate_path(self, path):
        # Logic for path validation
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            logger.info(f"Directory '{path}' created for {self.prefix}.")
        else:
            logger.info(f"Directory '{path}' already existed in {self.prefix}")

    @value_setter("file_path")
    def _filepath(self, path):
        pass

    def set_filepath(self, path):
        self._validate_path(path)
        self._filepath(path)

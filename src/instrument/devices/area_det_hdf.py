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

    def set_filepath(self, path):
        success = self._validate_path(path)
        if success:
            yield from self._filepath(path)

    @value_setter("file_name")
    def set_filename(self, filename):
        pass

    @value_setter("file_number")
    def set_filenumber(self, filenumber):
        pass

    def _validate_path(self, path):
        # Logic for path validation
        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
                logger.info(f"Directory '{path}' created for {self.prefix}.")
            else:
                logger.info(f"Directory '{path}' already existed in {self.prefix}")
            return 1

        except Exception as e:
                logger.error(f"Error creating directory {path} for {self.prefix}: {e}")
                return 0


    @value_setter("file_path")
    def _filepath(self, path):
        pass

    


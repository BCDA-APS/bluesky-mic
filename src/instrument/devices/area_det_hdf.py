# -*- coding: utf-8 -*-
"""
Created on Dec 03 2024

@author: yluo (grace227)
"""

from ophyd.areadetector.plugins import HDF5Plugin
from ophyd.areadetector.plugins import NetCDFPlugin
from ..devices.utils import mode_setter, value_setter
import os
import logging


logger = logging.getLogger(__name__)
logger.info(__file__)


class DetBase:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def sync_file_path(self, savedatapath, delimiter):
        p1 = self.file_path.get()
        p1_split = p1.split(delimiter)
        p2_split = savedatapath.split(delimiter)
        p1_new = p1_split[0] + delimiter + p2_split[-1]
        return p1_new

    # def set_filepath(self, path):
    #     yield from self._filepath(path)
    #     if self.file_path_exists.get():
    #         logger.info(f"File path is set to {self.file_path.get()}")
    #         return 1
    #     else:
    #         logger.info(f"File {self.file_path.get()} does not exist")
    #         return 0

    @value_setter("file_name")
    def set_filename(self, filename):
        pass

    @value_setter("file_number")
    def set_filenumber(self, filenumber):
        pass

    @value_setter("file_path")
    def set_filepath(self, path):
        pass

    @value_setter("capture")
    def set_capture(self, capture):
        pass

    @value_setter("num_capture")
    def set_num_capture(self, num_capture):
        pass


class DetHDF5(DetBase, HDF5Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class DetNetCDF(DetBase, NetCDFPlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

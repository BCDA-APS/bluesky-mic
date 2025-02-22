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
        """
        Synchronize the file path of the SaveData object with the EPICS AreaDetector filewriter.

        Parameters:
        - savedatapath: str
            The path where the files will be saved.
        - delimiter: str
            The delimiter used in the file path.
        """
        p1 = self.file_path.get()
        p1_split = p1.split(delimiter)
        p2_split = savedatapath.split(delimiter)
        p1_new = p1_split[0] + delimiter + p2_split[-1]
        return p1_new

    def generate_det_filepath(self, savedata, det_name):
        """
        Generate the file path and or create the directory
        for the EPICS AreaDetector filewriter.
        """
        basepath = savedata.get().file_system
        det_path = os.path.join(basepath, det_name.upper())
        logger.info(f"Setting up {det_name} to have data saved at {det_path}")
        if not os.path.exists(det_path):
            try:
                os.makedirs(det_path, exist_ok=True)
                logger.info(f"Directory '{det_path}' created for {det_name}.")
                return det_path
            except Exception as e:
                logger.error(
                    f"Failed to create directory '{det_path}' for {det_name}: {e}"
                )
                raise e

    def setup_file_writer(
        self,
        savedata,
        det_name,
        num_capture,
        filename="test_$id",
        beamline_delimiter="",
    ):
        """
        Set up the EPICS AreaDetector HDF5 filewriter.

        Parameters:
        - file_path: str
            The path where the files will be saved.
        - filename_pattern: str, optional
        - eiger_filewriter: The default file writer from Eiger (default is None).
        """

        # Stop capturing in case the filewriter is busy
        yield from self.set_capture("done")
        det_path = self.generate_det_filepath(savedata, det_name)
        newpath = self.sync_file_path(det_path, beamline_delimiter)

        yield from self.set_enable("Enable")
        yield from self.set_filepath(newpath)

        if self.file_path_exists.get():
            logger.info(f"File path is set to {self.file_path.get()}")
            yield from self.set_filenumber(0)
            yield from self.set_filename(filename)
            yield from self.set_num_capture(num_capture)
            yield from self.set_auto_save("yes")
            # yield from self.set_capture("capturing")
        else:
            logger.error(f"File path {self.file_path.get()} does not exist")
            raise ValueError(f"File path {self.file_path.get()} does not exist")

    @value_setter("file_name")
    def set_filename(self, filename):
        pass

    @value_setter("file_number")
    def set_filenumber(self, filenumber):
        pass

    @value_setter("file_path")
    def set_filepath(self, path):
        pass

    @value_setter("num_capture")
    def set_num_capture(self, num_capture):
        pass

    @mode_setter("capture")
    def set_capture(self, capture):
        pass

    @mode_setter("enable")
    def set_enable(self, mode):
        pass

    @mode_setter("auto_save")
    def set_auto_save(self, mode):
        pass


class DetHDF5(DetBase, HDF5Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class DetNetCDF(DetBase, NetCDFPlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

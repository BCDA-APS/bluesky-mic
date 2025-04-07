# -*- coding: utf-8 -*-
"""
Created on Dec 03 2024

@author: yluo (grace227)
"""

import logging
import os

from ophyd.areadetector.plugins import HDF5Plugin
from ophyd.areadetector.plugins import NetCDFPlugin

from mic_instrument.utils.device_utils import mode_setter
from mic_instrument.utils.device_utils import value_setter

logger = logging.getLogger(__name__)
logger.info(__file__)


class DetBase:
    """Base class for detector file plugins."""

    micdata_mountpath = ""

    def __init__(self, *args, **kwargs):
        """Initialize DetBase."""
        super().__init__(*args, **kwargs)

    def sync_file_path(self, det_path, delimiter):
        """
        Synchronize the file path of the SaveData object with the EPICS AreaDetector filewriter.

        Parameters:
        - det_path: str
            The path where the detector files will be saved.
        - delimiter: str
            The delimiter used in the file path.
        """
        fileplugin_path = self.file_path.get()
        fileplugin_path_split = fileplugin_path.split(delimiter)
        det_path_split = det_path.split(delimiter)
        fileplugin_path_new = fileplugin_path_split[0] + delimiter + det_path_split[-1]
        return fileplugin_path_new

    def generate_det_filepath(self, savedata, det_name):
        """
        Generate the file path and or create the directory
        for the EPICS AreaDetector filewriter.
        """
        basepath = savedata.get().file_system
        basepath = basepath.replace("//micdata/data1", self.micdata_mountpath)
        det_path = os.path.join(basepath, det_name.upper())
        logger.info(f"Setting up {det_name} to have data saved at {det_path}")
        if not os.path.exists(det_path):
            try:
                os.makedirs(det_path, exist_ok=True)
                logger.info(f"Directory '{det_path}' created for {det_name}.")
            except Exception as e:
                logger.error(
                    f"Failed to create directory '{det_path}' for {det_name}: {e}"
                )
                raise e
        return det_path

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
            if num_capture:
                yield from self.set_num_capture(num_capture)
            yield from self.set_auto_save("yes")
            # yield from self.set_capture("capturing")
        else:
            logger.error(f"File path {self.file_path.get()} does not exist")
            raise ValueError(f"File path {self.file_path.get()} does not exist")

    @value_setter("file_name")
    def set_filename(self, filename) -> None:
        """Set the file name for the file writer.

        Parameters:
            filename (str): The filename to set.
        """
        pass

    @value_setter("file_number")
    def set_filenumber(self, filenumber) -> None:
        """Set the file number for the file writer.

        Parameters:
            filenumber (int): The file number to set.
        """
        pass

    @value_setter("file_path")
    def set_filepath(self, path: str) -> None:
        """Set the file path for the file writer.

        Parameters:
            path (str): The file path to set.
        """
        pass

    @value_setter("num_capture")
    def set_num_capture(self, num_capture: int) -> None:
        """Set the number of captures for the file writer.

        Parameters:
            num_capture (int): The number of captures to set.
        """
        pass

    @mode_setter("capture")
    def set_capture(self, capture: str) -> None:
        """Set the capture mode for the file writer.

        Parameters:
            capture (str): The capture mode to set.
        """
        pass

    @mode_setter("enable")
    def set_enable(self, mode: str) -> None:
        """Set the enable mode for the file writer.

        Parameters:
            mode (str): The mode to enable.
        """
        pass

    @mode_setter("auto_save")
    def set_auto_save(self, mode: str) -> None:
        """Set the auto-save mode for the file writer.

        Parameters:
            mode (str): The auto-save mode to set.
        """
        pass


class DetHDF5(DetBase, HDF5Plugin):
    """HDF5 plugin for detector file writing."""

    def __init__(self, *args, **kwargs):
        """Initialize DetHDF5."""
        super().__init__(*args, **kwargs)


class DetNetCDF(DetBase, NetCDFPlugin):
    """NetCDF plugin for detector file writing."""

    def __init__(self, *args, **kwargs):
        """Initialize DetNetCDF."""
        super().__init__(*args, **kwargs)

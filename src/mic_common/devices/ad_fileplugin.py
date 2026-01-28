# -*- coding: utf-8 -*-
"""
Created on Dec 03 2024

@author: yluo (grace227)
"""

import logging
import os

from apsbits.core.instrument_init import oregistry

from ophyd.areadetector.plugins import HDF5Plugin
from ophyd.areadetector.plugins import NetCDFPlugin

from mic_common.utils.device_utils import mode_setter
from mic_common.utils.device_utils import value_setter
from mic_common.utils.device_utils import unstage_with_skip
from mic_common.devices.save_data import SaveDataMic

logger = logging.getLogger(__name__)
logger.info(__file__)

# savedata = oregistry["savedata"]

class DetBase:
    """Base class for detector file plugins."""

    micdata_mountpath: str = ""
    data_path: str = ""
    delimiter: str = ""
    det_foldername: str = ""
    savedata: SaveDataMic = None
    filename: str = "test_$id"

    def __init__(self, *args, **kwargs):
        """Initialize DetBase."""
        super().__init__(*args, **kwargs)

    def update_filename(self):
        """Update the filename based on the savedata."""
        self.savedata.update_next_file_name()
        self.filename = self.savedata.next_file_name.replace(".mda", "")

    def sync_file_path(self, det_path):
        """
        Synchronize the file path of the SaveData object with the EPICS AreaDetector
        filewriter.

        Parameters:
        - det_path: str
            The path where the detector files will be saved.
        """
        fileplugin_path = self.file_path.get()
        if fileplugin_path.startswith(self.micdata_mountpath[0]) and self.micdata_mountpath not in fileplugin_path:
            fileplugin_path = fileplugin_path.replace(self.micdata_mountpath[0], self.micdata_mountpath)
        elif fileplugin_path == "":
            return det_path
        
        fileplugin_path_split = fileplugin_path.split(self.delimiter)
        det_path_split = det_path.split(self.delimiter)
        fileplugin_path_new = fileplugin_path_split[0] + self.delimiter + det_path_split[-1]
        return fileplugin_path_new

    def generate_det_filepath(self):
        """
        Generate the file path and or create the directory
        for the EPICS AreaDetector filewriter.
        """
        basepath = self.savedata.file_system.get()
        basepath = basepath.replace("//micdata/data1/", self.micdata_mountpath)
        det_path = os.path.join(basepath, self.det_foldername.upper())
        logger.info(f"Setting up {self.det_foldername} to have data saved at {det_path}")
        if not os.path.exists(det_path) and "W:" not in det_path:
            try:
                os.makedirs(det_path, exist_ok=True)
                logger.info(f"Directory '{det_path}' created for {self.det_foldername}.")
                return det_path
            except Exception as e:
                logger.error(
                    f"Failed to create directory '{det_path}' for {self.det_foldername}: {e}"
                )
                raise e
        if det_path.startswith("W") and "W:" not in det_path:
            det_path.replace("W", "W:")
            return det_path

        return det_path

    def config_file_writer(
        self,
        num_capture,
        next_filenum=0,
        is19ID=False,
        **kwargs,
    ):
        """
        Set up the EPICS AreaDetector HDF5 filewriter.

        Parameters:
        - file_path: str
            The path where the files will be saved.
        - filename_pattern: str, optional
        - eiger_filewriter: The default file writer from Eiger (default is None).
        """

        det_path = self.generate_det_filepath()
        self.update_filename()
        if is19ID:
            newpath = det_path
        else:
            newpath = self.sync_file_path(det_path)

        self.stage_sigs["capture"] = 0
        self.stage_sigs["enable"] = 1
        self.stage_sigs["file_path"] = newpath
        self.stage_sigs["file_number"] = next_filenum
        self.stage_sigs["file_name"] = self.filename
        self.stage_sigs["num_capture"] = num_capture
        self.stage_sigs["auto_save"] = 1

    # def setup_file_writer(
    #     self,
    #     det_name,
    #     num_capture,
    #     next_filenum=0,
    #     filename="test_$id",
    #     beamline_delimiter="",
    #     is19ID=False,
    # ):
    #     """
    #     Set up the EPICS AreaDetector HDF5 filewriter.

    #     Parameters:
    #     - file_path: str
    #         The path where the files will be saved.
    #     - filename_pattern: str, optional
    #     - eiger_filewriter: The default file writer from Eiger (default is None).
    #     """

    #     # Stop capturing in case the filewriter is busy
    #     yield from self.set_capture("done")
    #     det_path = self.generate_det_filepath(self.savedata, det_name)
    #     if is19ID:
    #         newpath = det_path
    #     else:
    #         newpath = self.sync_file_path(det_path, beamline_delimiter)

    #     yield from self.set_enable("Enable")
    #     yield from self.set_filepath(newpath)

    #     if self.file_path_exists.get():
    #         logger.info(f"File path is set to {self.file_path.get()}")
    #         yield from self.set_filenumber(next_filenum)
    #         yield from self.set_filename(filename)
    #         if num_capture:
    #             yield from self.set_num_capture(num_capture)
    #         yield from self.set_auto_save("yes")
    #         # yield from self.set_capture("capturing")
    #     else:
    #         logger.error(f"File path {self.file_path.get()} does not exist")
    #         raise ValueError(f"File path {self.file_path.get()} does not exist")

    # @value_setter("file_name")
    # def set_filename(self, filename) -> None:
    #     """Set the file name for the file writer.

    #     Parameters:
    #         filename (str): The filename to set.
    #     """
    #     pass

    # @value_setter("file_number")
    # def set_filenumber(self, filenumber) -> None:
    #     """Set the file number for the file writer.

    #     Parameters:
    #         filenumber (int): The file number to set.
    #     """
    #     pass

    # @value_setter("file_path")
    # def set_filepath(self, path: str) -> None:
    #     """Set the file path for the file writer.

    #     Parameters:
    #         path (str): The file path to set.
    #     """
    #     pass

    # @value_setter("num_capture")
    # def set_num_capture(self, num_capture: int) -> None:
    #     """Set the number of captures for the file writer.

    #     Parameters:
    #         num_capture (int): The number of captures to set.
    #     """
    #     pass

    # @mode_setter("capture")
    # def set_capture(self, capture: str) -> None:
    #     """Set the capture mode for the file writer.

    #     Parameters:
    #         capture (str): The capture mode to set.
    #     """
    #     pass

    # @mode_setter("enable")
    # def set_enable(self, mode: str) -> None:
    #     """Set the enable mode for the file writer.

    #     Parameters:
    #         mode (str): The mode to enable.
    #     """
    #     pass

    # @mode_setter("auto_save")
    # def set_auto_save(self, mode: str) -> None:
    #     """Set the auto-save mode for the file writer.

    #     Parameters:
    #         mode (str): The auto-save mode to set.
    #     """
    #     pass

    def unstage(self):
        """Unstage the device but avoid restoring file_path and file_name from stage_sigs.

        Uses the unstage_with_skip utility to prevent certain fields from being
        restored during unstage.
        """
        fields_to_skip = ["file_path", "file_name", "num_capture", "file_number"]
        unstage_with_skip(self, fields_to_skip)
        return super().unstage()


class DetHDF5(DetBase, HDF5Plugin):
    """HDF5 plugin for detector file writing."""

    def __init__(self, *args, **kwargs):
        """Initialize DetHDF5."""
        super().__init__(*args, **kwargs)
        self.capture.put(0)


class DetNetCDF(DetBase, NetCDFPlugin):
    """NetCDF plugin for detector file writing."""

    def __init__(self, *args, **kwargs):
        """Initialize DetNetCDF."""
        # kwargs["prefix"] = kwargs["prefix"] + ":"
        super().__init__(*args, **kwargs)
        self.capture.put(0)

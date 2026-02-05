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
        # self.capture.put(0)


class DetNetCDF(DetBase, NetCDFPlugin):
    """NetCDF plugin for detector file writing."""

    def __init__(self, *args, **kwargs):
        """Initialize DetNetCDF."""
        super().__init__(*args, **kwargs)
        # self.capture.put(0)

"""
Created on Dec 04 2024

@author: yluo (grace227)
"""

import logging
import os
import pathlib
from apstools.synApps import SaveData

from mic_common.utils.device_utils import value_setter

logger = logging.getLogger(__name__)
logger.info(__file__)


class SaveDataMic(SaveData):
    """SaveData device for MIC instrument."""

    next_file_name: str = ""
    current_file_name: str = ""
    micdata_mountpath: str = ""
    storage_path: str = ""

    def __init__(self, *args, **kwargs):
        """Initialize SaveDataMic."""
        super().__init__(*args, **kwargs)
        try:
            self.update_next_file_name()
        except Exception as e: 
            logger.error(f"Fail to update next file name")
        logger.info(f"Next mda file is: {self.next_file_name}")

    def update_next_file_name(self):
        """Update the next file name based on scan number."""
        next_scan_number = str(self.get().next_scan_number).zfill(4)
        current_scan_number = str(self.get().next_scan_number - 1).zfill(4)
        self.current_file_name = f"{self.get().base_name}{current_scan_number}.mda"
        self.next_file_name = f"{self.get().base_name}{next_scan_number}.mda"

    def generate_det_path(self, det_name):
        base_path = self.file_system.get()
        det_path = os.path.join(base_path, det_name.upper())
        logger.info(f"Setting up {det_name} to have data saved at {det_path}")
        if not os.path.exists(det_path):
            try:
                os.makedirs(det_path)
                logger.info(f"Directory '{det_path}' created for {det_name}.")
            except Exception as e:
                logger.error(
                    f"Failed to create directory '{det_path}' for {det_name}: {e}"
                )
                raise e
        return det_path
    
    def advance_scan_number(self):
        current_scan_number = self.next_scan_number.get()
        self.next_scan_number.put(current_scan_number+1)


    def update_current_file_name(self):
        """Update the current file name based on scan number."""
        current_scan_number = str(self.get().next_scan_number - 1).zfill(4)
        self.current_file_name = f"{self.get().base_name}{current_scan_number}.mda"
        logger.info(f"Current mda file is: {self.current_file_name}")

    def get_storage_path(self):
        basepath = self.file_system.get()
        storage_path = basepath.replace(self.micdata_mountpath, self.storage_path)
        return storage_path

    @value_setter("file_system")
    def set_file_system(self, path):
        """Set file system path."""
        pass

    @value_setter("subdirectory")
    def set_subdir(self, subdir):
        """Set subdirectory path."""
        pass

    @value_setter("base_name")
    def set_basename(self, basename):
        """Set base name for files."""
        pass

    @value_setter("next_scan_number")
    def set_next_scan_number(self, next_scan_number):
        """Set next scan number."""
        pass

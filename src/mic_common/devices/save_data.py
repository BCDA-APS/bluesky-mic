"""
Created on Dec 04 2024

@author: yluo (grace227)
"""

import logging

from apstools.synApps import SaveData

from mic_common.utils.device_utils import value_setter

logger = logging.getLogger(__name__)
logger.info(__file__)


class SaveDataMic(SaveData):
    """SaveData device for MIC instrument."""

    next_file_name = ""

    def __init__(self, *args, **kwargs):
        """Initialize SaveDataMic."""
        super().__init__(*args, **kwargs)

    def update_next_file_name(self):
        """Update the next file name based on scan number."""
        next_scan_number = str(self.get().next_scan_number).zfill(4)
        self.next_file_name = f"{self.get().base_name}{next_scan_number}.mda"
        logger.info(f"Next mda file is: {self.next_file_name}")

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

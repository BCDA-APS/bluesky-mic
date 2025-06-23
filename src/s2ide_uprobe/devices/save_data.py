"""
Created on Dec 04 2024

@author: yluo (grace227)
"""

import logging

from apstools.synApps import SaveData

from ..devices.utils import value_setter

logger = logging.getLogger(__name__)
logger.info(__file__)


class SaveDataMic(SaveData):
    """Custom SaveData class for handling file naming and directory structure for scans."""

    next_file_name = ""

    def __init__(self, *args, **kwargs):
        """Initialize SaveDataMic with optional arguments."""
        super().__init__(*args, **kwargs)

    def update_next_file_name(self) -> None:
        """Update the next file name for the scan and log the new name."""
        next_scan_number = str(self.get().next_scan_number).zfill(4)
        self.next_file_name = f"{self.get().base_name}{next_scan_number}.mda"
        logger.info(f"Next mda file is: {self.next_file_name}")

    @value_setter("file_system")
    def set_file_system(self, path: str) -> None:
        """Set the file system path for saving data."""
        pass

    @value_setter("subdirectory")
    def set_subdir(self, subdir: str) -> None:
        """Set the subdirectory for saving data."""
        pass

    @value_setter("base_name")
    def set_basename(self, basename: str) -> None:
        """Set the base name for the scan files."""
        pass

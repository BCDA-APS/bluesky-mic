"""
Created on Dec 04 2024

@author: yluo (grace227)
"""

import logging

from apstools.synApps import SaveData

from .utils import value_setter

logger = logging.getLogger(__name__)
logger.info(__file__)


class SaveDataMic(SaveData):
    next_file_name = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def update_next_file_name(self):
        next_scan_number = str(self.get().next_scan_number).zfill(4)
        self.next_file_name = f"{self.get().base_name}{next_scan_number}.mda"
        logger.info(f"Next mda file is: {self.next_file_name}")

    @value_setter("file_system")
    def set_file_system(self, path):
        pass

    @value_setter("subdirectory")
    def set_subdir(self, subdir):
        pass

    @value_setter("base_name")
    def set_basename(self, basename):
        pass

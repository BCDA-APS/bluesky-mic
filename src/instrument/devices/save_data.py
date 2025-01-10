"""
Created on Dec 04 2024

@author: yluo (grace227)
"""

import logging
from apstools.synApps import SaveData
from ..devices.utils import value_setter
import bluesky.plan_stubs as bps
from ..utils.config_loaders import iconfig

logger = logging.getLogger(__name__)
logger.info(__file__)


class SaveDataMic(SaveData):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @value_setter("file_system")
    def set_file_system(self, path):
        pass

    @value_setter("subdirectory")
    def set_subdir(self, subdir):
        pass

    @value_setter("base_name")
    def set_basename(self, basename):
        pass

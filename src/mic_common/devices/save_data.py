"""
Created on Dec 04 2024

@author: yluo (grace227)
"""

import logging
import os
import pathlib
from apstools.synApps import SaveData

from mic_common.utils.device_utils import value_setter

from isn.utils.run_engine import RE

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

    def generate_det_path(self, det_name):
        base_path = self.file_system.get()
        subdirectory = self.subdirectory.get()
        try:
            scan_number = RE.md['scan_id']+1
        except:
            scan_number = self.next_scan_number.get()
        det_path = os.path.join(base_path, 
                                subdirectory,
                                'Raw', 
                                f'Scan_{scan_number:04d}', 
                                det_name.upper())
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
    
    def generate_det_path_windows(self, det_name, linux_root, windows_root):
        """Generate the detector save path for a Windows-hosted IOC.

        Unlike ``generate_det_path``, the base path is not ``file_system`` (a
        gdata drive the Windows machine cannot mount) but the shared micdata
        mount, which both machines can see at different roots. The scan folder is
        created via the Linux view (``linux_root``) and the equivalent Windows
        path (rooted at ``windows_root``, using backslash separators) is returned
        so it can be written to the IOC's ``file_path`` PV.
        """
        subdirectory = self.subdirectory.get()
        try:
            scan_number = RE.md['scan_id']+1
        except:
            scan_number = self.next_scan_number.get()
        rel_path = os.path.join(subdirectory,
                                'Raw',
                                f'Scan_{scan_number:04d}',
                                det_name.upper())
        linux_path = os.path.join(linux_root, rel_path)
        logger.info(f"Setting up {det_name} to have data saved at {linux_path}")
        if not os.path.exists(linux_path):
            try:
                os.makedirs(linux_path)
                logger.info(f"Directory '{linux_path}' created for {det_name}.")
            except Exception as e:
                logger.error(
                    f"Failed to create directory '{linux_path}' for {det_name}: {e}"
                )
                raise e
        windows_path = os.path.join(windows_root, rel_path).replace("/", "\\")
        if not windows_path.endswith("\\"):
            windows_path += "\\"
        logger.info(f"Windows path for {det_name}: {windows_path}")
        return windows_path

    def advance_scan_number(self):
        current_scan_number = self.next_scan_number.get()
        self.next_scan_number.put(current_scan_number+1)
        

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

"""
eiger500k.py

Author: grace227 (yluo89)
Date: 2025-02-14
Description: This module defines the Eiger500k class, which inherits from
EigerDetectorCam to control the Eiger 500k detector. It provides methods to set up
external triggers and manage acquisition parameters for the detector.

"""

import logging
import os
from typing import Any
from typing import Generator

from ophyd import Component
from ophyd import EigerDetectorCam
from ophyd import EpicsSignal

from mic_common.utils.device_utils import mode_setter
from mic_common.utils.device_utils import value_setter

logger = logging.getLogger(__name__)
logger.info(__file__)


class Eiger500k(EigerDetectorCam):
    """
    Eiger500k class inherits from EigerDetectorCam to control the Eiger 500k detector.

    This class provides methods to set up external triggers and manage acquisition
    parameters.
    """

    file_writer_enable = Component(EpicsSignal, "FWEnable")
    file_compression = Component(EpicsSignal, "FWCompression")
    num_images_per_file = Component(EpicsSignal, "FWNImagesPerFile")
    file_name_pattern = Component(EpicsSignal, "FWNamePattern")
    save_files = Component(EpicsSignal, "SaveFiles")

    def sync_file_path(self, savedatapath: str, delimiter: str) -> str:
        """
        Synchronize the file path of the SaveData object with the EPICS AreaDetector
        filewriter.

        Parameters:
        - savedatapath: str
            The path where the files will be saved.
        - delimiter: str
            The delimiter used in the file path.

        Returns:
        str: The new synchronized file path.
        """
        p1 = self.file_path.get()
        print(p1)
        print(delimiter)
        p1_split = p1.split(delimiter)
        print(p1_split)
        p2_split = savedatapath.split(delimiter)
        print(p2_split)
        p1_new = p1_split[0] + delimiter + p2_split[-1]
        print(p1_new)
        return p1_new

    def setup_external_enable_trigger(
        self, num_triggers: int
    ) -> Generator[None, None, None]:
        """
        Set up the external enable trigger for the detector.

        Parameters:
        - num_triggers: Number of triggers to be set.
        - pixel_dwell: Dwell time for each pixel in milliseconds.
        - exp_factor: Exposure factor to adjust the acquisition time (default is 1).
        - ad_hdf5_filewriter: The EPICS AreaDetector HDF5 filewriter to be set up
          (default is None).

        Yields:
        None: This is a generator yielding from internal methods to configure triggers.
        """
        yield from self.set_num_triggers(num_triggers)  # Set the number of triggers
        yield from self.set_num_images(1)  # Set the number of images to 1

    def setup_external_series_trigger(
        self, num_triggers: int
    ) -> Generator[None, None, None]:
        """
        Set up the external series trigger for the detector.

        Parameters:
        - num_triggers: Number of triggers to be set.
        - pixel_dwell: Dwell time for each pixel in milliseconds.
        - exp_factor: Exposure factor to adjust the acquisition time (default is 1).

        Yields:
        None: This is a generator yielding from internal methods to configure triggers.
        """
        # Set the number of images to the number of triggers
        yield from self.set_num_images(num_triggers)
        yield from self.set_num_triggers(1)  # Set the number of triggers to 1

    def setup_eiger_filewriter(
        self, savedata: Any, det_name: str, filename: str, beamline_delimiter: str
    ) -> Generator[None, None, None]:
        """
        Set up the default Eiger filewriter.
        """
        print(beamline_delimiter)
        basepath = savedata.get().file_system
        det_path = os.path.join(basepath, det_name.upper())
        logger.info(f"Setting up {det_name} to have data saved at {det_path}")
        if not os.path.exists(det_path):
            os.makedirs(det_path, exist_ok=True)
            logger.info(f"Directory '{det_path}' created for {det_name}.")

        newpath = self.sync_file_path(det_path, beamline_delimiter)
        yield from self.set_file_path(newpath)

        if self.file_path_exists.get():
            yield from self.set_file_writer_enable("Enable")
            yield from self.set_file_name_pattern(filename.replace(".mda", ""))
            self.ready = True
        else:
            logger.error(f"File path {newpath} does not exist")

    def flyscan_before(
        self, num_pulses: int, dwell: float, ptycho_exp_factor: float
    ) -> Generator[None, None, None]:
        """
        Set up the Eiger detector for a flyscan.
        """
        trigger_mode = self.trigger_mode.get(as_string=True)
        yield from self.set_acquire("Stop")

        if trigger_mode == "External Series":
            yield from self.setup_external_series_trigger(num_pulses)
        elif trigger_mode == "External Enable":
            yield from self.setup_external_enable_trigger(num_pulses)

        yield from self.set_num_triggers(num_pulses)
        yield from self.set_acquire_period(dwell / 1000)
        yield from self.set_acquire_time(dwell / 1000 / ptycho_exp_factor)

    @mode_setter("file_writer_enable")
    def set_file_writer_enable(self, mode: str) -> Generator[None, None, None]:
        """
        Set the file writer enable mode.

        Parameters:
        - mode: The mode to set for the file writer enable signal.

        Yields:
        None
        """
        pass

    @mode_setter("acquire")
    def set_acquire(self, mode: str) -> Generator[None, None, None]:
        """
        Set the acquire mode for the detector.

        Parameters:
        - mode: The mode to set for the acquisition process.

        Yields:
        None
        """
        pass

    @value_setter("file_path")
    def set_file_path(self, value: str) -> Generator[None, None, None]:
        """
        Set the file path for the detector.

        Parameters:
        - value: The new file path to be set.

        Yields:
        None
        """
        pass

    @value_setter("file_name_pattern")
    def set_file_name_pattern(self, value: str) -> Generator[None, None, None]:
        """
        Set the file name pattern for the file writer.

        Parameters:
        - value: The file name pattern to be set.

        Yields:
        None
        """
        pass

    @value_setter("acquire_period")
    def set_acquire_period(self, value: float) -> Generator[None, None, None]:
        """
        Set the acquire period for the detector.

        Parameters:
        - value: The acquire period value to be set.

        Yields:
        None
        """
        pass

    @value_setter("acquire_time")
    def set_acquire_time(self, value: float) -> Generator[None, None, None]:
        """
        Set the acquire time for the detector.

        Parameters:
        - value: The acquire time value to be set.

        Yields:
        None
        """
        pass

    @value_setter("num_images")
    def set_num_images(self, value: int) -> Generator[None, None, None]:
        """
        Set the number of images for the detector.

        Parameters:
        - value: The number of images to be set.

        Yields:
        None
        """
        pass

    @value_setter("num_triggers")
    def set_num_triggers(self, value: int) -> Generator[None, None, None]:
        """
        Set the number of triggers for the detector.

        Parameters:
        - value: The number of triggers to be set.

        Yields:
        None
        """
        pass

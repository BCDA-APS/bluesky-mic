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
import time
from typing import Any
from typing import Generator

from ophyd import Component, Device, EpicsSignal, Staged
from ophyd import EigerDetectorCam

from mic_common.devices.ad_fileplugin import DetHDF5
from mic_common.utils.device_utils import mode_setter, value_setter, LoggingStageSigs

logger = logging.getLogger(__name__)
logger.info(__file__)


class EigerBase(EigerDetectorCam):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        original_stage_sigs = self.stage_sigs
        self.stage_sigs = LoggingStageSigs(original_stage_sigs, prefix=self.prefix)

    def config(
        self, 
        num_pulses: int,
        dwell_time: float, # unit in seconds
        trigger_mode: int = 2, # 2: "external series"
        num_triggers: int = 1, # number of triggers
        **kwargs):

        self.stage_sigs.clear()
        self.stage_sigs['acquire'] = 0
        self.stage_sigs['trigger_mode'] = trigger_mode
        self.stage_sigs['acquire_time'] = dwell_time
        self.stage_sigs['acquire_period'] = dwell_time
        self.stage_sigs['num_images'] = num_pulses
        self.stage_sigs['num_triggers'] = num_triggers
        

class Eiger2ID(Device):
    cam = Component(EigerBase, ":cam1:", kind="config", labels=("eiger2id", "cam"))
    fileplugin = Component(DetHDF5, ":HDF1:", kind="config", labels=("eiger2id", "fileplugin"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.fileplugin.stage_sigs.pop("parent.cam.array_callbacks", None)
            logger.info("Removing array_callbacks stage signal from Eiger2ID fileplugin")
        except Exception as e:
            logger.error(f"Error removing array_callbacks stage signal from Eiger2ID fileplugin: {e}")
            raise e

    def config_flyscan(self, num_pulses: int = None, dwell_time: float = None, **kwargs):
        """Configure the Eiger2ID device for a flyscan with the given points and dwell time."""
        self.unstage()
        try:
            self.cam.config(num_pulses, dwell_time, **kwargs)
        except Exception as e:
            logger.error(f"Error configuring cam for fly scan: {e}")
            raise e

        try:
            self.fileplugin.config_file_writer(num_pulses, **kwargs)
            self.fileplugin.stage_sigs.pop("parent.cam.array_callbacks", None)
        except Exception as e:
            logger.error(f"Error configuring fileplugin for fly scan: {e}")
            raise e

    def unstage(self):
        """Unstage the Eiger2ID device."""
        # Check if device is already staged and unstage if necessary
        if self._staged == Staged.yes:
            logger.info("Eiger2ID is unstaged, unstaging ... ...")
            return super().unstage()
        elif self._staged == Staged.partially:
            logger.info("Eiger2ID is partially staged, unstaging cam and fileplugin separately...")
            if self.cam._staged == Staged.yes:
                self.cam.unstage()
            if self.fileplugin._staged == Staged.yes:
                self.fileplugin.unstage()

    def unhang(self, retries: int = 1, delay_s: float = 0.1) -> dict[str, object]:
        attempts = max(1, int(retries))
        results: list[dict[str, object]] = []
        for attempt in range(1, attempts + 1):
            print(f"Attempt {attempt} to unhang Eiger2ID")
            try:
                self.cam.acquire.put(0)
                self.fileplugin.capture.put(0)
                results.append({"attempt": attempt, "success": True})
                if attempt < attempts and delay_s > 0:
                    time.sleep(delay_s)
            except Exception as exc:
                logger.exception("Failed to unhang Eiger2ID on attempt %s", attempt)
                results.append({"attempt": attempt, "success": False, "error": str(exc)})
                return {
                    "device": self.name,
                    "success": False,
                    "retries": attempts,
                    "attempts": results,
                }
        return {
            "device": self.name,
            "success": True,
            "retries": attempts,
            "attempts": results,
        }

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

    def scan_init(self, exposure_time, num_images, ptycho_exp_factor):
        """
        Initialize the detector for a scan.
        Based on the current trigger mode, this function will choose corresponding setup functions.

        Parameters:
        - dwell: Dwell time for each pixel in seconds.
        - num_images: Number of images to be set.
        - ptycho_exp_factor: Exposure factor to adjust the acquisition time.
                             When is set to 1, the exposure time is the same as the dwell time.
                             Otherwise, the exposure time is the dwell time divided by the ptycho_exp_factor.
        """
        trigger_mode = self.trigger_mode.get(as_string=True)
        print(f"trigger_mode: {trigger_mode}")
        yield from self.set_acquire("DONE")

        if trigger_mode == "Internal":
            yield from self.setup_internal_trigger(num_images)
        elif trigger_mode == "External Enable":
            yield from self.setup_external_enable_trigger(num_images)
        elif trigger_mode == "External Series":
            yield from self.setup_external_series_trigger(num_images)

        yield from self.set_acquire_period(exposure_time)
        yield from self.set_acquire_time(exposure_time / ptycho_exp_factor)

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

    def setup_external_enable_trigger(self, num_triggers: int) -> Generator[None, None, None]:
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

    def setup_external_series_trigger(self, num_triggers: int) -> Generator[None, None, None]:
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

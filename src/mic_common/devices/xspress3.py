# -*- coding: utf-8 -*-
"""
Created on Dec 04 2024

@author: yluo (grace227)
"""
# TODO: Add back the colon

import datetime
import logging

from ophyd import Component
from ophyd import EpicsSignal
from ophyd.areadetector.cam import Xspress3DetectorCam

from mic_common.utils.device_utils import mode_setter
from mic_common.utils.device_utils import value_setter
from mic_common.utils.writeDetH5 import write_det_h5

logger = logging.getLogger(__name__)
logger.info(__file__)


class Xspress3(Xspress3DetectorCam):
    """Xspress3 detector camera for X-ray spectroscopy."""

    erase_on_start = Component(EpicsSignal, ":EraseOnStart")

    def __init__(self, *args, **kwargs):
        """Initialize Xspress3 detector."""
        super().__init__(*args, **kwargs)

    def scan_init(self, exposure_time=0, num_images=0):
        """Initialize scan parameters.

        Parameters:
            exposure_time (float): Exposure time in seconds.
            num_images (int): Number of images to acquire.
        """
        yield from self.set_acquire_time(exposure_time)
        yield from self.set_num_images(num_images)

    def write_h5(
        self, masterfile_path: str, detector_path: str, scan_name: str, det_name: str
    ):
        """Write detector data to HDF5 file.

        Parameters:
            masterfile_path (str): Path to master file.
            detector_path (str): Path to detector data.
            scan_name (str): Name of the scan.
            det_name (str): Name of the detector.
        """
        logger.info(
            f"{self.__class__.__name__}: Writing HDF5 file to {masterfile_path}"
        )
        logger.info(f"{self.__class__.__name__}: Detector path: {detector_path}")
        logger.info(f"{self.__class__.__name__}: Scan name: {scan_name}")

        det_file_ext = ".hdf5"
        det_key = "/entry"

        attrs_values = {}
        attrs_values.update({"datetime": str(datetime.datetime.now())})
        attrs_values.update({"acquire_time": self.acquire_time.get()})
        attrs_values.update({"num_images": self.num_images.get()})
        attrs_values.update({"num_frames_saved": self.frame_count.get()})

        trigger_mode = self.trigger_mode.enum_strs[self.trigger_mode.get()]
        attrs_values.update({"trigger_mode": trigger_mode})

        write_det_h5(
            masterfile_path=masterfile_path,
            det_dir=detector_path,
            scan_name=scan_name,
            det_name=det_name,
            det_file_ext=det_file_ext,
            det_key=det_key,
            det_attrs_values=attrs_values,
        )

    @mode_setter("image_mode")
    def set_image_mode(mode):
        """Set image acquisition mode."""
        pass

    @mode_setter("erase_on_start")
    def set_erase_on_start(mode):
        """Set erase on start mode."""
        pass

    @mode_setter("trigger_mode")
    def set_trigger_mode(mode):
        """Set trigger mode."""
        pass

    @value_setter("acquire_time")
    def set_acquire_time(exposure_time):
        """Set acquisition time."""
        pass

    @value_setter("num_images")
    def set_num_images(num_images):
        """Set number of images to acquire."""
        pass

    @value_setter("acquire")
    def set_acquire_state(value):
        """Set acquisition state."""
        pass

    # @value_setter("acquire")
    # def stop_acquire(value = 0):
    #     pass

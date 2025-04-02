"""
eiger500k.py

Author: grace227 (yluo89)
Date: 2025-02-14
Description: This module defines the Eiger1M class, which inherits from EigerDetectorCam
to control the Eiger 1M detector. It provides methods to set up external triggers and manage
acquisition parameters for the detector.

"""

from ophyd import EigerDetectorCam
from mic_instrument.devices.utils import mode_setter, value_setter
from mic_instrument.utils.writeDetH5 import write_det_h5
from ophyd import Component, EpicsSignal, EpicsSignalRO
import logging
import os
import datetime
logger = logging.getLogger(__name__)
logger.info(__file__)


class Eiger1M(EigerDetectorCam):
    """
    Eiger1M class inherits from EigerDetectorCam to control the Eiger 1M detector.

    This class provides methods to set up external triggers and manage acquisition parameters.
    """

    threshold1_enable = Component(EpicsSignal, ":Threshold1Enable")
    threshold2_enable = Component(EpicsSignal, ":Threshold2Enable")
    threshold_diff_enable = Component(EpicsSignal, ":ThresholdDiffEnable")
    threshold1_value = Component(EpicsSignal, ":ThresholdEnergy")
    threshold2_value = Component(EpicsSignal, ":Threshold2Energy")

    det_size_x = Component(EpicsSignalRO, ":MaxSizeX_RBV")
    det_size_y = Component(EpicsSignalRO, ":MaxSizeY_RBV")
    pix_size_x = Component(EpicsSignalRO, ":XPixelSize_RBV")
    pix_size_y = Component(EpicsSignalRO, ":YPixelSize_RBV")
    sensor_thickness = Component(EpicsSignalRO, ":SensorThickness_RBV")
    det_description = Component(EpicsSignalRO, ":Description_RBV")

    file_writer_enable = Component(EpicsSignal, ":FWEnable")
    file_compression = Component(EpicsSignal, ":FWCompression")
    num_images_per_file = Component(EpicsSignal, ":FWNImagesPerFile")
    file_name_pattern = Component(EpicsSignal, ":FWNamePattern")
    save_files = Component(EpicsSignal, ":SaveFiles")


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
        yield from self.set_acquire("Stop")

        if trigger_mode == "Internal":
            yield from self.setup_internal_trigger(num_images)
        elif trigger_mode == "External Enable":
            yield from self.setup_external_enable_trigger(num_images)
        elif trigger_mode == "External Series":
            yield from self.setup_external_series_trigger(num_images)
        
        yield from self.set_acquire_period(exposure_time)
        yield from self.set_acquire_time(exposure_time / ptycho_exp_factor)


    def write_h5(self, 
                 masterfile_path: str, 
                 detector_path: str, 
                 scan_name: str,
                 det_name: str):
                
        logger.info(f"{self.__class__.__name__}: Writing HDF5 file to {masterfile_path}")
        logger.info(f"{self.__class__.__name__}: Detector path: {detector_path}")
        logger.info(f"{self.__class__.__name__}: Scan name: {scan_name}")

        det_file_ext = ".h5"
        det_key = "/entry"

        attrs_values = {}
        attrs_values.update({"datetime": str(datetime.datetime.now())})
        attrs_values.update({"acquire_time": self.acquire_time.get()})
        attrs_values.update({"acquire_period": self.acquire_period.get()})
        attrs_values.update({"num_images": self.num_images.get()})
        attrs_values.update({"num_exposures_per_img": self.num_exposures.get()})
        attrs_values.update({"num_triggers": self.num_triggers.get()})
        attrs_values.update({"trigger_mode": self.trigger_mode.get(as_string=True)})
        
        attrs_values.update({"threshold1_enable": self.threshold1_enable.get()})
        attrs_values.update({"threshold2_enable": self.threshold2_enable.get()})
        attrs_values.update({"threshold_diff_enable": self.threshold_diff_enable.get()})
        attrs_values.update({"threshold1_eV": self.threshold1_value.get()})
        attrs_values.update({"threshold2_eV": self.threshold2_value.get()})
        attrs_values.update({"photon_energy_eV": self.photon_energy.get()})

        attrs_values.update({"det_size_x": self.det_size_x.get()})
        attrs_values.update({"det_size_y": self.det_size_y.get()})
        attrs_values.update({"pix_size_x": self.pix_size_x.get()})
        attrs_values.update({"pix_size_y": self.pix_size_y.get()})
        attrs_values.update({"det_dist_mm": self.det_distance.get()})
        attrs_values.update({"sensor_thickness": self.sensor_thickness.get()})
        attrs_values.update({"det_description": self.det_description.get()})
        

        write_det_h5(masterfile_path = masterfile_path, 
                     det_dir = detector_path, 
                     scan_name = scan_name, 
                     det_name = det_name, 
                     det_file_ext = det_file_ext, 
                     det_key = det_key, 
                     det_attrs_values = attrs_values)
        

    def sync_file_path(self, savedatapath, delimiter):
        """
        Synchronize the file path of the SaveData object with the EPICS AreaDetector filewriter.

        Parameters:
        - savedatapath: str
            The path where the files will be saved.
        - delimiter: str
            The delimiter used in the file path.
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

    def setup_internal_trigger(self, num_triggers):
        """
        Set up the internal trigger for the detector.
        This function will set the number of images equals to the input number of triggers
        and the number of triggers equals to 1.

        This is essentially the same as the setup_external_series_trigger function.
        """
        yield from self.setup_external_series_trigger(num_triggers)
    
    def setup_external_enable_trigger(self, num_triggers):
        """
        Set up the external enable trigger for the detector.
        This function will set the number of triggers equals to the input number of triggers
        and the number of images equals to 1.
        Parameters:
        - num_triggers: Number of triggers to be set.
        """
        yield from self.set_num_triggers(num_triggers)  # Set the number of triggers
        yield from self.set_num_images(1)  # Set the number of images to 1

    def setup_external_series_trigger(self, num_triggers):
        """
        Set up the external series trigger for the detector.
        This function will set the number of images equals to the input number of triggers
        and the number of triggers equals to 1.
        Parameters:
        - num_triggers: Number of triggers to be set.
        """
        yield from self.set_num_images(
            num_triggers
        )  # Set the number of images to the number of triggers
        yield from self.set_num_triggers(1)  # Set the number of triggers to 1

    def setup_eiger_filewriter(self, savedata, det_name, filename, beamline_delimiter):
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

    def flyscan_before(self, num_pulses, dwell, ptycho_exp_factor):
        """
        Set up the Eiger detector for a flyscan.

        Parameters:
        - num_pulses: Number of pulses to be set.
        - dwell: Dwell time for each pixel in milliseconds.
        - ptycho_exp_factor: Exposure factor to adjust the acquisition time.
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
    def set_file_writer_enable(self, mode):
        pass

    @mode_setter("acquire")
    def set_acquire(self, mode):
        pass

    @value_setter("file_path")
    def set_file_path(self, value):
        pass

    @value_setter("file_name_pattern")
    def set_file_name_pattern(self, value):
        pass

    @value_setter("acquire_period")
    def set_acquire_period(self, value):
        pass

    @value_setter("acquire_time")
    def set_acquire_time(self, value):
        pass

    @value_setter("num_images")
    def set_num_images(self, value):
        pass

    @value_setter("num_triggers")
    def set_num_triggers(self, value):
        pass

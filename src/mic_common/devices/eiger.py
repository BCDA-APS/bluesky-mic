from ophyd import (
    ADComponent,
    Component,
    EpicsSignal,
    EpicsSignalRO
)
from ophyd.areadetector import (
    SingleTrigger,
    EigerDetectorCam, 
    DetectorBase,
    ImagePlugin,
    HDF5Plugin,
    StatsPlugin,
    ROIPlugin,
    ADTriggerStatus,
    Staged
)

from apstools.utils import run_in_thread
from time import sleep


class Trigger(SingleTrigger):

    _status = ADTriggerStatus
    
    def __init__(self, *args, min_period=0.2, **kwargs):
        super().__init__(*args, **kwargs)
        self._acquisition_signal_pv = "cam1."
        self._min_period = min_period

    def setup_internal_trigger(self):
        self.cam.stage_sigs["trigger_mode"] = "Internal Enable"
        self.cam.stage_sigs["manual_trigger"] = "Enable"
        self.cam.stage_sigs["num_images"] = 1
        self.cam.stage_sigs["num_exposures"] = 1
        self.cam.stage_sigs["num_triggers"] = int(1e5)

    def stage(self):
        '''Staging detector. Must ensure that stage signals are well defined previously.'''

        #Guarantee we are not collecting
        self.cam.acquire.set(0).wait(timeout=10)
        super().stage()
        self.cam.acquire.set(1).wait(timeout=10)

    def trigger(self):
        if self._staged != Staged.yes:
            raise RuntimeError("This detector is not ready to trigger."
                               "Call the stage() method before triggering.")
        
        @run_in_thread
        def exposure_delay(status_obj):
            delay = self.cam.acquire_time.get()
            sleep(delay)
            status_obj.set_finished()

        self._status = self._status_type(self)
        self.cam.special_trigger_button.put(1, wait=False)
        exposure_delay(self._status)
        return self._status

    def unstage(self):
        super().unstage()
        self.cam.acquire.set(0).wait(timeout=10)
    


class EigerCam(EigerDetectorCam):

    threshold1_enable = ADComponent(EpicsSignal, "Threshold1Enable", kind='config')
    threshold2_enable = ADComponent(EpicsSignal, "Threshold2Enable", kind='config')
    threshold_diff_enable = ADComponent(EpicsSignal, "ThresholdDiffEnable", kind='config')
    threshold1_energy = ADComponent(EpicsSignal, "ThresholdEnergy", kind='config')
    threshold2_energy = ADComponent(EpicsSignal, "Threshold2Energy", kind='config')
    counting_mode = ADComponent(EpicsSignal, "CountingMode", kind="config")
    
    det_size_x = ADComponent(EpicsSignalRO, "MaxSizeX_RBV")
    det_size_y = ADComponent(EpicsSignalRO, "MaxSizeY_RBV")
    pix_size_x = ADComponent(EpicsSignalRO, "XPixelSize_RBV")
    pix_size_y = ADComponent(EpicsSignalRO, "YPixelSize_RBV")
    sensor_thickness = ADComponent(EpicsSignalRO, "SensorThickness_RBV")
    det_description = ADComponent(EpicsSignalRO, "Description_RBV")

    file_writer_enable = ADComponent(EpicsSignal, "FWEnable", kind='config')
    file_compression = ADComponent(EpicsSignal, "FWCompression", kind='config')
    num_images_per_file = ADComponent(EpicsSignal, "FWNImagesPerFile", kind='config')
    file_name_pattern = ADComponent(EpicsSignal, "FWNamePattern", kind='config')
    save_files = ADComponent(EpicsSignal, "SaveFiles", kind='config')

    _default_configuration_attrs = EigerDetectorCam._default_configuration_attrs + (
        'threshold1_enable',
        'threshold2_enable',
        'threshold_diff_enable',
        'threshold1_energy',
        'threshold2_energy',
        'counting_mode')
    


class Eiger(Trigger, DetectorBase):

    cam = ADComponent(EigerCam, ':cam1:')
    # image = ADComponent(ImagePlugin, 'image1:')
    # stats = ADComponent(StatsPlugin, 'stats1:')
    hdf5 = ADComponent(HDF5Plugin, ':HDF1:')
    # roi1 = ADComponent(ROIPlugin, 'ROI1:')
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

    _status_type = ADTriggerStatus
    
    def __init__(self, *args, min_period=0.2, **kwargs):
        super().__init__(*args, **kwargs)
        self._acquisition_signal_pv = "cam1:Acquire"
        self._min_period = min_period

    def setup_internal_trigger(self, num_images=None):
        self.cam.stage_sigs["trigger_mode"] = "Internal Enable"
        self.cam.stage_sigs["manual_trigger"] = "Enable"
        if not num_images:
            self.cam.stage_sigs["num_images"] = 1
            self.cam.stage_sigs["num_triggers"] = int(1e5)
        else:
            self.cam.stage_sigs["num_images"] = num_images
            self.cam.stage_sigs["num_triggers"] = num_images
        self.cam.stage_sigs["num_exposures"] = 1

    def setup_flyscan_mode(self, num_images=1, acq_time=0.01):
        self.cam.stage_sigs["num_triggers"] = num_images
        self.cam.stage_sigs.move_to_end("num_triggers", last=False)
        self.cam.stage_sigs["num_images"] = num_images
        self.cam.stage_sigs["trigger_mode"] = "External Enable"
        self.cam.stage_sigs["acquire_time"] = acq_time
        self.cam.stage_sigs["acquire_period"]= acq_time
        self.cam.stage_sigs["manual_trigger"] = "Disable"
        self.cam.stage_sigs["num_exposures"] = 1


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

    threshold1_enable = Component(EpicsSignal, "Threshold1Enable", kind='config')
    threshold2_enable = Component(EpicsSignal, "Threshold2Enable", kind='config')
    threshold_diff_enable = Component(EpicsSignal, "ThresholdDiffEnable", kind='config')
    threshold1_energy = Component(EpicsSignal, "ThresholdEnergy", kind='config')
    threshold2_energy = Component(EpicsSignal, "Threshold2Energy", kind='config')
    counting_mode = Component(EpicsSignal, "CountingMode", kind="config")
    
    det_size_x = Component(EpicsSignalRO, "MaxSizeX_RBV")
    det_size_y = Component(EpicsSignalRO, "MaxSizeY_RBV")
    pix_size_x = Component(EpicsSignalRO, "XPixelSize_RBV")
    pix_size_y = Component(EpicsSignalRO, "YPixelSize_RBV")
    sensor_thickness = Component(EpicsSignalRO, "SensorThickness_RBV")
    det_description = Component(EpicsSignalRO, "Description_RBV")

    file_writer_enable = Component(EpicsSignal, "FWEnable", kind='config')
    file_compression = Component(EpicsSignal, "FWCompression", kind='config')
    num_images_per_file = Component(EpicsSignal, "FWNImagesPerFile", kind='config')
    file_name_pattern = Component(EpicsSignal, "FWNamePattern", kind='config')
    save_files = Component(EpicsSignal, "SaveFiles", kind='config')

    _default_configuration_attrs = EigerDetectorCam._default_configuration_attrs + (
        'threshold1_enable',
        'threshold2_enable',
        'threshold_diff_enable',
        'threshold1_energy',
        'threshold2_energy',
        'counting_mode')
    


class Eiger(Trigger, DetectorBase):

    cam = ADComponent(EigerCam, 'cam1:')
    image = ADComponent(ImagePlugin, 'image1:')
    hdf1 = ADComponent(HDF5Plugin, 'HDF1:')


    roi1 = ADComponent(ROIPlugin, 'ROI1:')
    roi2 = ADComponent(ROIPlugin, 'ROI2:')
    roi3 = ADComponent(ROIPlugin, 'ROI3:')
    roi4 = ADComponent(ROIPlugin, 'ROI4:')
    stats1 = ADComponent(StatsPlugin, 'Stats1:')
    stats2 = ADComponent(StatsPlugin, 'Stats2:')
    stats3 = ADComponent(StatsPlugin, 'Stats3:')
    stats4 = ADComponent(StatsPlugin, 'Stats4:')
    stats5 = ADComponent(StatsPlugin, 'Stats5:')



    def align_on(self, time=0.1):
        """Start detector in alignment mode"""
        self.save_images_off()
        self.cam.manual_trigger.set("Disable").wait(timeout=10)
        self.cam.num_triggers.set(int(1e9)).wait(timeout=10)
        self.cam.trigger_mode.set("Continuous").wait(timeout=10)
        self.preset_monitor.set(time).wait(timeout=10)
        self.cam.acquire.set(1).wait(timeout=10)

    def align_off(self):
        """Stop detector"""
        self.cam.acquire.set(0).wait(timeout=10)

    def save_images_on(self):
        self.hdf1.enable.set("Enable").wait(timeout=10)

    def save_images_off(self):
        self.hdf1.enable.set("Disable").wait(timeout=10)

    def auto_save_on(self):
        self.hdf1.autosave.put("on")

    def auto_save_off(self):
        self.hdf1.autosave.put("off")

    def plot_all(self):
        self.plot_select([1, 2, 3, 4, 5])

    def plot_stats1(self):
        self.plot_select([1])

    def plot_stats2(self):
        self.plot_select([2])

    def plot_stats3(self):
        self.plot_select([3])

    def plot_stats4(self):
        self.plot_select([4])

    def plot_stats5(self):
        self.plot_select([5])



    def plot_select(self, stats):
        """
        Selects which stats will be plotted. All are being read.

        This assumes that 5 stats are setup in Bluesky.

        PARAMETERS
        ----------
        stats : iterable of ints
            List with the stats numbers to be plotted.
        """

        for i in range(1, 5+1):
            getattr(self, f"stats{i}").total.kind = (
                "hinted" if i in stats else "normal"
            )
            getattr(self, f"stats{i}").enable.put(
                1 if i in stats else 0
            )
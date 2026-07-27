import datetime
import logging

from ophyd import (
    ADComponent,
    EpicsSignal,
    Component
)
from ophyd.areadetector import (
    ADTriggerStatus,
    DetectorBase,
    ImagePlugin,
    OverlayPlugin,
    ROIPlugin,
    SingleTrigger,
    StatsPlugin,
)
from ophyd.areadetector.cam import AndorDetectorCam

from apstools.devices import CamMixin_V34
from mic_common.devices.andor_fileplugin import WindowsHDF5
from mic_common.utils.writeDetH5 import write_det_h5

logger = logging.getLogger(__name__)

MAX_IMAGES = int(1e4)

# READOUT_TIME_SEC = {"FVB": 0.006, "Image":0.118}



class Trigger(SingleTrigger):
    _status_type = ADTriggerStatus
    # trigger_mode = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_soft_trigger()
        self.cam.acquire_period.tolerance = 1
        self.cam.accumulate_period.tolerance = 1

    def setup_soft_trigger(self, num_images=1, hdf_images=MAX_IMAGES):
        self.cam.stage_sigs["trigger_mode"] = "Internal"
        self.cam.stage_sigs["image_mode"] = "Multiple"
        self.cam.stage_sigs["num_exposures"] = int(num_images)
        self.hdf1.stage_sigs["num_capture"] = int(hdf_images)

    def setup_flyscan_mode(self, num_images=1, acq_time=0.01, hdf_images=MAX_IMAGES):
        self.trigger_mode = "Flyscan"
        if acq_time < 0.006:
            raise 'Andor camera limit reached. Acquire time must be greater than 6 ms.'
        
        self.cam.stage_sigs["readout_mode"] = 0
        
        self.cam.stage_sigs["trigger_mode"] = "External"
        self.cam.stage_sigs["image_mode"] = "Multiple"
        self.cam.stage_sigs["num_images"] = num_images
        self.cam.stage_sigs["num_exposures"] = 1
        self.cam.stage_sigs["acquire_time"] = float(acq_time-0.006)
        self.cam.stage_sigs["acquire_period"] = float(acq_time)
        self.cam.stage_sigs["accumulate_period"] = float(acq_time)
        
        # self.cam.stage_sigs["acquire"] = 1

        self.hdf1.stage_sigs["enable"] = 1
        self.hdf1.stage_sigs["auto_save"] = 1
        self.hdf1.stage_sigs["num_capture"] = int(hdf_images)

        # self.cam.stage_sigs.move_to_end("accumulate_period", last=False)
        # self.cam.stage_sigs.move_to_end("acquire_period", last=False)


    def stage(self):
        self.cam.acquire.put(0)
        if self.trigger_mode == "Flyscan":
            # self.cam.readout_mode.set(0).wait()
            self.cam.acquire_time.set(0).wait()
            self.cam.acquire_period.set(0).wait()
            self.cam.accumulate_period.set(0).wait()
        super().stage()
        if self.trigger_mode == "Flyscan":
            self.cam.acquire.set(1).wait()

    def unstage(self):
        self.cam.acquire.put(0)
        return super().unstage()


class AndorCam(CamMixin_V34, AndorDetectorCam):

    _default_configuration_attrs = AndorDetectorCam._default_configuration_attrs + (
        "acquire_time",
        "acquire_period",
        "image_mode",
        "trigger_mode",
        "num_images",
    )

    accumulate_period = Component(EpicsSignal, "AndorAccumulatePeriod")
    readout_mode = Component(EpicsSignal, "AndorReadOutMode")


class Andor(Trigger, DetectorBase):
    cam = ADComponent(AndorCam, "cam1:")
    image = ADComponent(ImagePlugin, "image1:")
    hdf1 = ADComponent(WindowsHDF5, "HDF1:")
    over1 = ADComponent(OverlayPlugin, "Over1:")

    roi1 = ADComponent(ROIPlugin, "ROI1:")
    roi2 = ADComponent(ROIPlugin, "ROI2:")
    roi3 = ADComponent(ROIPlugin, "ROI3:")
    roi4 = ADComponent(ROIPlugin, "ROI4:")
    stats1 = ADComponent(StatsPlugin, "Stats1:")
    stats2 = ADComponent(StatsPlugin, "Stats2:")
    stats3 = ADComponent(StatsPlugin, "Stats3:")
    stats4 = ADComponent(StatsPlugin, "Stats4:")
    stats5 = ADComponent(StatsPlugin, "Stats5:")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # All ROI, stats, image, and overlay plugins are disabled on staging
        # by default. Call enable_plugins() before a scan to activate the
        # ones you need.
        self.image.disable_on_stage()
        self.over1.disable_on_stage()
        # over1 is lazy=True so PVs don't connect at init. Do not access
        # self.over1 here — leave it untouched until explicitly needed.
        for i in range(1, 5):
            getattr(self, f"roi{i}").disable_on_stage()
        for i in range(1, 6):
            getattr(self, f"stats{i}").disable_on_stage()

    def enable_plugins(self, stats=(), rois=()):
        """Configure which plugins are enabled during staging.

        Call before running a plan. Settings persist until the next call.

        Parameters
        ----------
        stats : iterable of int
            Stats plugin numbers to enable, e.g. (1, 2).
        rois : iterable of int
            ROI plugin numbers to enable, e.g. (1,).
        """
        for i in range(1, 5):
            plugin = getattr(self, f"roi{i}")
            plugin.enable_on_stage() if i in rois else plugin.disable_on_stage()
        for i in range(1, 6):
            plugin = getattr(self, f"stats{i}")
            plugin.enable_on_stage() if i in stats else plugin.disable_on_stage()

    def align_on(self, time=0.1):
        self.save_images_off()
        self.cam.trigger_mode.set("Internal").wait(timeout=10)
        self.cam.image_mode.set("Continuous").wait(timeout=10)
        self.cam.acquire_time.set(time).wait(timeout=10)
        self.cam.acquire.set(1).wait(timeout=10)

    def align_off(self):
        self.cam.acquire.set(0).wait(timeout=10)

    def save_images_on(self):
        self.hdf1.enable.set("Enable").wait(timeout=10)

    def save_images_off(self):
        self.hdf1.enable.set("Disable").wait(timeout=10)

    def auto_save_on(self):
        self.hdf1.auto_save.put("1")

    def auto_save_off(self):
        self.hdf1.auto_save.put("0")

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
        for i in range(1, 6):
            getattr(self, f"stats{i}").total.kind = "hinted" if i in stats else "normal"
            getattr(self, f"stats{i}").enable.put(1 if i in stats else 0)

    def write_master_h5(
        self,
        masterfile_path="",
        detector_path="",
        scan_name="",
        det_name="",
        det_file_ext=".h5",
        det_key="/entry",
    ):
        logger.info(
            f"{self.__class__.__name__}: Writing HDF5 file to {masterfile_path}"
        )
        logger.info(f"{self.__class__.__name__}: Detector path: {detector_path}")
        logger.info(f"{self.__class__.__name__}: Scan name: {scan_name}")

        attrs_values = {"datetime": str(datetime.datetime.now())}
        write_det_h5(
            masterfile_path=masterfile_path,
            det_dir=detector_path,
            scan_name=scan_name,
            det_name=det_name,
            det_file_ext=det_file_ext,
            det_key=det_key,
            det_attrs_values=attrs_values,
        )
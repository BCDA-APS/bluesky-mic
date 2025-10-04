"""AD mixins"""

from ophyd import (
    ADComponent,
    EpicsSignal,
    Signal,
    Component,
    BlueskyInterface,
    OphydObject
)
from ophyd.areadetector import (
    EigerDetectorCam,
    Xspress3DetectorCam,
    EpicsSignalWithRBV,
)
from ophyd.areadetector.plugins import (
    PluginBase_V34,
    ImagePlugin_V34,
    PvaPlugin_V34,
    ROIPlugin_V34,
    StatsPlugin_V34,
    CodecPlugin_V34,
    HDF5Plugin_V34,
    ROIStatPlugin_V34,
    ROIStatNPlugin_V25,
    AttributePlugin_V34,
    ProcessPlugin_V34,
    TransformPlugin_V34,
)
from ophyd.areadetector.filestore_mixins import FileStoreBase
from ophyd.areadetector.trigger_mixins import (
    ADTriggerStatus as ophyd_ADTriggerStatus
)
from ophyd.status import UnknownStatusFailure
from apstools.devices import CamMixin_V34
from os.path import isfile
from itertools import count
from pathlib import Path
from collections import OrderedDict
from logging import getLogger
from time import sleep, time as ttime

logger = getLogger(__name__)

USE_DM_PATH = True
DM_ROOT_PATH = "/gdata/dm/4IDD"


class PluginMixin(PluginBase_V34):
    """Remove property attribute found in AD IOCs now."""

    _asyn_pipeline_configuration_names = None


class TransformPlugin(PluginMixin, TransformPlugin_V34):
    """Remove property attribute found in AD IOCs now."""


class ImagePlugin(PluginMixin, ImagePlugin_V34):
    """Remove property attribute found in AD IOCs now."""


class PvaPlugin(PluginMixin, PvaPlugin_V34):
    """Remove property attribute found in AD IOCs now."""


class ProcessPlugin(PluginMixin, ProcessPlugin_V34):
    """Remove property attribute found in AD IOCs now."""


class ROIPlugin(PluginMixin, ROIPlugin_V34):
    """Remove property attribute found in AD IOCs now."""

    _default_configuration_attrs = (
        ROIPlugin_V34._default_configuration_attrs
        + (
            "driver_version",
            "data_type",
            "color_mode",
            "enable",
            "enable_scale",
            "scale",
            "collapse_dims",
            "dimensions",
            "data_type_out",
            "name_",
            "roi_enable",
            "bin_",
            "min_xyz",
            "size",
            "reverse",
        )
    )


class StatsPlugin(PluginMixin, StatsPlugin_V34):
    """Remove property attribute found in AD IOCs now."""

    _default_configuration_attrs = (
        StatsPlugin_V34._default_configuration_attrs
        + (
            "array_size",
            "blocking_callbacks",
            "color_mode",
            "data_type",
            "dimensions",
            "enable",
            "driver_version",
            "compute_statistics",
            "bgd_width",
            "compute_centroid",
            "centroid_threshold",
            "compute_profiles",
            "profile_average",
            "profile_centroid",
            "profile_cursor",
            "profile_size",
            "profile_threshold",
            "cursor",
            "compute_histogram",
            "hist_entropy",
            "hist_max",
            "hist_min",
            "hist_size",
            "histogram",
            "hist_above",
            "hist_below",
            "histogram_x",
        )
    )

    _default_read_attrs = StatsPlugin_V34._default_read_attrs + (
        "max_value",
        "max_xy.x",
        "max_xy.y",
        "mean_value",
        "min_value",
        "min_xy.x",
        "min_xy.y",
        "net",
        "total",
        "centroid.x",
        "centroid.y",
        "sigma_xy",
        "sigma.x",
        "sigma.y",
        "orientation",
        "kurtosis",
        "skew",
        "centroid_total",
        "eccentricity",
    )

    # These generates confusion as it's the exact same as sigma.x and .y
    sigma_x = None
    sigma_y = None

    # This is to auto-set the kind depending on what is being computed.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compute_statistics.subscribe(self._control_stats)
        self.compute_centroid.subscribe(self._control_centroid)
        self.compute_profiles.subscribe(self._control_profile)
        self.compute_histogram.subscribe(self._control_histogram)

    def start_auto_kind(self):
        self.compute_statistics.subscribe(self._control_stats)
        self.compute_centroid.subscribe(self._control_centroid)
        self.compute_profiles.subscribe(self._control_profile)
        self.compute_histogram.subscribe(self._control_histogram)

    def stop_auto_kind(self):
        for item in (
            "compute_statistics",
            "compute_centroid",
            "compute_profiles",
            "compute_histogram",
        ):
            getattr(self, item).unsubscribe_all()

    def _control_stats(self, value, **kwargs):
        items = (
            "bgd_width",
            "max_value",
            "min_value",
            "max_xy",
            "max_xy.x",
            "max_xy.y",
            "min_xy",
            "min_xy.x",
            "min_xy.y",
            "total",
            "net",
            "mean_value",
            "sigma_value",
        )
        k = "normal" if value == "Yes" else "omitted"
        for item in items:
            getattr(self, item).kind = k

    def _control_centroid(self, value, **kwargs):
        items = (
            "centroid",
            "centroid.x",
            "centroid.y",
            "sigma_xy",
            "sigma",
            "sigma.x",
            "sigma.y",
            "centroid_total",
            "eccentricity",
            "orientation",
            "kurtosis",
            "skew",
        )
        k = "normal" if value == "Yes" else "omitted"
        for item in items:
            getattr(self, item).kind = k

    def _control_profile(self, value, **kwargs):
        items = [item for item in self.component_names if "profile" in item]
        k = "normal" if value == "Yes" else "omitted"
        for item in items:
            getattr(self, item).kind = k

    def _control_histogram(self, value, **kwargs):
        items = [item for item in self.component_names if "hist" in item]
        k = "normal" if value == "Yes" else "omitted"
        for item in items:
            getattr(self, item).kind = k


class CodecPlugin(PluginMixin, CodecPlugin_V34):
    """Remove property attribute found in AD IOCs now."""


class ROIStatPlugin(PluginMixin, ROIStatPlugin_V34):
    """Remove property attribute found in AD IOCs now."""


class ROIStatNPlugin(PluginMixin, ROIStatNPlugin_V25):
    """Remove property attribute found in AD IOCs now."""


class AttributePlugin(PluginMixin, AttributePlugin_V34):
    """Remove property attribute found in AD IOCs now."""

    ts_acquiring = None
    ts_control = None
    ts_current_point = None
    ts_num_points = None
    ts_read = None


class EigerDetectorCam(CamMixin_V34, EigerDetectorCam):
    """Revise EigerDetectorCam for ADCore revisions."""

    initialize = ADComponent(EpicsSignal, "Initialize", kind="config")
    counting_mode = ADComponent(EpicsSignal, "CountingMode", kind="config")

    # These components not found on Eiger 4M at 8-ID-I
    file_number_sync = None
    file_number_write = None
    fw_clear = None
    link_0 = None
    link_1 = None
    link_2 = None
    link_3 = None
    dcu_buff_free = None
    offset = None


class VortexDetectorCam(CamMixin_V34, Xspress3DetectorCam):
    trigger_mode = Component(EpicsSignalWithRBV, "TriggerMode", kind="config")
    erase_on_start = Component(
        EpicsSignal, "EraseOnStart", string=True, kind="config"
    )
    soft_trigger = ADComponent(EpicsSignal, "SoftTrigger")

    # Removed
    offset = None
    num_exposures = None
    acquire_period = None


class FileStorePluginBaseEpicsName(FileStoreBase):

    def __init__(self, *args, ioc_path_root=None, **kwargs):
        super().__init__(*args, **kwargs)
        # if hasattr(self, "create_directory"):
        #     self.stage_sigs.update({"create_directory": -3})
        self.stage_sigs.update(
            [
                ("create_directory", -3),
                ("auto_increment", "Yes"),
                ("array_counter", 0),
                ("auto_save", "Yes"),
                ("num_capture", 0),
            ]
        )
        # This is needed if you want to start bluesky and run a no-image scan
        # first.
        self._fn = None
        self._fp = None
        self._use_dm = USE_DM_PATH
        self._ioc_path_root = ioc_path_root

    @property
    def use_dm(self):
        return self._use_dm

    @use_dm.setter
    def use_dm(self, value):
        if isinstance(value, bool):
            self._use_dm = value
        else:
            raise ValueError(
                f"use_dm must be set to True or False, but {value} was entered."
            )

    def make_write_read_paths(self, path=None):
        # This will generate the folder name and the full path.
        # - Folder is either determined by data management, or just use the one
        # in EPICS.
        # - File name uses everything from EPICS (template, base name and file
        # number).

        # Setting up the path.
        # If not using DM, it will simply take the values from EPICS!!
        if path is None:
            path = Path(self.file_path.get())

        # Create full path based on EPICS file template - assumes some sort of
        # %s%s_5.5%d.h5 format
        full_path = self.file_template.get() % (
            str(path) + "/",
            self.file_name.get(),
            int(self.file_number.get()),
        )

        relative_path = self.file_template.get() % (
            f"{self.parent.name}/",
            self.file_name.get(),
            int(self.file_number.get()),
        )

        return str(path), full_path, relative_path

    def stage(self):

        # Only save images if the enable is on...
        if self.enable.get() in (True, 1, "on", "Enable"):

            if self.file_write_mode.get(as_string=True) != "Single":
                self.capture.set(0).wait()

            path, full_path, _ = self.make_write_read_paths()

            if isfile(full_path):
                raise OSError(
                    f"{full_path} already exists! Cannot overwrite it, so "
                    "please change the file name."
                )

            if not self.file_path_exists.get():
                raise IOError(
                    f"Path {self.file_path.get()} does not exist on IOC."
                )

            self.file_path.set(path).wait(timeout=10)

            super().stage()

            self._fn = full_path
            self._fp = full_path


class FileStoreHDF5IterativeWriteEpicsName(FileStorePluginBaseEpicsName):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filestore_spec = "AD_HDF5"  # spec name stored in resource doc
        self.stage_sigs.update(
            [
                ("file_template", "%s%s_%6.6d.h5"),
                ("file_write_mode", "Stream"),
                ("capture", 1),
            ]
        )
        self._point_counter = None
        # TODO: Come up with a better way to do this... AtributeSignal?
        self._num_images_device = "cam.num_images"

    @property
    def _num_images_signal(self):
        return getattr(self.root, self._num_images_device)

    def get_frames_per_point(self):
        num_capture = self.num_capture.get()
        # If num_capture is 0, then the plugin will capture however many frames
        # it is sent. We can get how many frames it will be sent (unless
        # interrupted) by consulting num_images on the detector's camera.
        if num_capture == 0:
            return self._num_images_signal.get()
        # Otherwise, a nonzero num_capture will cut off capturing at the
        # specified number.
        return num_capture

    def stage(self):
        super().stage()
        res_kwargs = {"frame_per_point": self.get_frames_per_point()}
        if self._fn is None:
            self._fn = self.reg_root
        self._generate_resource(res_kwargs)
        self._point_counter = count()

    def unstage(self):
        self._point_counter = None
        super().unstage()

    def generate_datum(self, key, timestamp, datum_kwargs):
        i = next(self._point_counter)
        datum_kwargs = datum_kwargs or {}
        datum_kwargs.update({"point_number": i})
        return super().generate_datum(key, timestamp, datum_kwargs)


class HDF5Plugin(PluginMixin, HDF5Plugin_V34):
    pass


class PolarHDF5Plugin(HDF5Plugin, FileStoreHDF5IterativeWriteEpicsName):
    """
    Using the filename from EPICS.
    """

    _default_configuration_attrs = HDF5Plugin._default_configuration_attrs + (
        "auto_increment",
        "auto_save",
        "file_format",
        "file_name",
        "file_number",
        "file_path",
        "file_path_exists",
        "file_template",
        "file_write_mode",
        "array_size",
        "color_mode",
        "data_type",
        "dimensions",
        "enable",
        "plugin_type",
        "compression",
        "szip_num_pixels",
        "store_attr",
        "store_perform",
        "zlevel",
        "xml_file_name",
        "swmr_active",
        "swmr_cb_counter",
        "swmr_mode",
        "swmr_supported",
        "driver_version",
        "blosc_compressor",
        "blosc_level",
        "blosc_shuffle",
        "autosave",
    )
    _default_read_attrs = HDF5Plugin._default_read_attrs + ("full_file_name",)

    autosave = ADComponent(Signal, value="off", kind="config")

    def __init__(self, *args, write_path_template="", **kwargs):
        # self.filestore_spec = "AD_EIGER_APSPolar"
        super().__init__(
            *args, write_path_template=write_path_template, **kwargs
        )
        # self.enable.subscribe(self._setup_kind, run=False)
        self._warmup_signals = []

    def _setup_kind(self, value, **kwargs):
        if value in (True, 1, "on", "Enable"):
            self.kind = "normal"
        else:
            self.kind = "omitted"

    def stage(self):
        if self.autosave.get() in (True, 1, "on", "Enable"):
            self.parent.save_images_on()
        super().stage()

    def unstage(self):
        if self.autosave.get() in (True, 1, "on", "Enable"):
            self.parent.save_images_off()
        super().unstage()

    @property
    def warmup_signals(self):
        return OrderedDict(self._warmup_signals)
    
    @warmup_signals.setter
    def warmup_signals(self, values):
        try:
            for (sig, _) in list(values):
                if not isinstance(sig, OphydObject):
                    raise ValueError(
                        "warmup signal must be a list of "
                        "(OphydObject, value) tuples."
                    )
            self._warmup_signals = values
        except TypeError:
            raise TypeError(
                "warmup signal must be a list of (signal, value) tuples."
            )

    def warmup(self):
        if len(self.warmup_signals) == 0:
            logger.warning(
                f"The there are no warmup signals for {self.parent.name}"
            )

        original_vals = {sig: sig.get() for sig in self.warmup_signals}

        try:
            for sig, val in self.warmup_signals.items():
                sleep(0.1)  # abundance of caution
                sig.set(val).wait()

            sleep(2)  # wait for acquisition

            for sig, val in reversed(list(original_vals.items())):
                sleep(0.1)
                sig.set(val).wait()
        except UnknownStatusFailure as exc:
            logger.error(
                "The device {self.name} could not be warmed up because it "
                "could not connect to a device with the following exception: "
                f"{exc}."
            )

class TriggerBase(BlueskyInterface):
    """Base class for trigger mixin classes

    Subclasses must define a method with this signature:

    ``acquire_changed(self, value=None, old_value=None, **kwargs)``
    """

    def __init__(
        self,
        *args,
        acquisition_signal_dev="cam.acquire",
        acquire_busy_signal_dev="cam.acquire_busy",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        # settings
        # careful here: quadEM devices have areadetector components but,
        # they have no 'cam' plugin. See QuadEM initializer.
        if hasattr(self, "cam"):
            self.stage_sigs.update(
                [
                    ("cam.acquire", 0),  # If acquiring, stop
                    ("cam.image_mode", 1),  # 'Multiple' mode
                ]
            )
            self._acquisition_signal_dev = acquisition_signal_dev
            self._acquire_busy_signal_dev = acquire_busy_signal_dev

        self._status = None

    @property
    def _acquisition_signal(self):
        return getattr(self, self._acquisition_signal_dev)

    @property
    def _acquire_busy_signal(self):
        return getattr(self, self._acquire_busy_signal_dev)


class ADTriggerStatus(ophyd_ADTriggerStatus):
    def _notify_watchers(self, value, *args, **kwargs):
        # *args and **kwargs catch extra inputs from pyepics, not needed here
        if self.done:
            self.device.cam.array_counter.clear_sub(self._notify_watchers)
        if not self._watchers:
            return
        # Always start progress bar at 0 regardless of starting value of
        # array_counter.
        current = value - self._initial_count
        target = self._target_count
        initial = 0
        time_elapsed = ttime() - self.start_ts
        try:
            fraction = 1 - (current - initial) / (target - initial)
        except ZeroDivisionError:
            fraction = 0
        except Exception:
            fraction = None
            time_remaining = None
        else:
            time_remaining = (
                None if fraction == 0 else time_elapsed / fraction
            )
        for watcher in self._watchers:
            watcher(
                name=self._name,
                current=current,
                initial=initial,
                target=target,
                unit="images",
                precision=0,
                fraction=fraction,
                time_elapsed=time_elapsed,
                time_remaining=time_remaining,
            )
from ophyd import Device
from ophyd import Component
from ophyd import EpicsSignal
from ophyd import EpicsSignalWithRBV
from ophyd import EpicsSignalRO
from ophyd import Staged
from ophyd import SignalRO
from ophyd import DynamicDeviceComponent

from ophyd.areadetector import ADComponent
from ophyd.areadetector import Xspress3DetectorCam
from ophyd.areadetector import DetectorBase
from ophyd.areadetector.trigger_mixins import TriggerBase
from ophyd.areadetector.trigger_mixins import ADTriggerStatus
from ophyd.areadetector.plugins import ROIPlugin
from ophyd.areadetector.plugins import ROIStatPlugin

from apstools.devices import CamMixin_V34

from .mic_ad_mixins import MicHDF5

from collections import OrderedDict

from time import sleep


MAX_IMAGES = 12216
MAX_ROIS = 8

# class Trigger(TriggerBase):
#     """
#     This trigger mixin class takes one acquisition per trigger.
#     """

#     _status_type = ADTriggerStatus

#     def __init__(self, *args, image_name=None, **kwargs):
#         super().__init__(*args, **kwargs)
#         if image_name is None:
#             image_name = "_".join([self.name, "image"])
#         self._image_name = image_name
#         self._acquisition_signal = self.cam.acquire
#         self._acquire_busy_signal = self.cam.acquire_busy
#         self._flysetup = False
#         self._status = None

#     def setup_manual_trigger(self):
#         # Stage signals
#         self.cam.stage_sigs["trigger_mode"] = "Internal"
#         self.cam.stage_sigs["num_images"] = 1
#         self.cam.stage_sigs["wait_for_plugins"] = "Yes"

#     def setup_external_trigger(self):
#         # Stage signals
#         self.cam.stage_sigs["trigger_mode"] = "TTL Veto Only"
#         self.cam.stage_sigs["num_images"] = MAX_IMAGES
#         self.cam.stage_sigs["wait_for_plugins"] = "No"

#     def stage(self):

#         self.cam.erase.set(1).wait(timeout=10)

#         if self._flysetup:
#             self.setup_external_trigger()

#         # Make sure that detector is not armed.
#         self._acquisition_signal.set(0).wait(timeout=10)
#         self._acquire_busy_signal.subscribe(self._acquire_changed)

#         # super().stage()
#         self.cam.stage()

#         if self._flysetup:
#             self._acquisition_signal.set(1).wait(timeout=10)

#         # self._staged = True
#         super().stage()

#     def unstage(self):
#         super().unstage()
#         self.cam.acquire.set(0).wait(timeout=10)
#         self._flysetup = False
#         self._acquire_busy_signal.clear_sub(self._acquire_changed)
#         self._collect_image = False
#         self.setup_manual_trigger()

#     def trigger(self):
#         if self._staged != Staged.yes:
#             raise RuntimeError(
#                 "This detector is not ready to trigger."
#                 "Call the stage() method before triggering."
#             )

#         # Click the Acquire_button
#         self._status = self._status_type(self)
#         self._acquisition_signal.put(1, wait=False)
#         # if self.hdf1.enable.get() in (True, 1, "on", "Enable"):
#         #     self.generate_datum(self._image_name, ttime(), {})

#         return self._status

#     def _acquire_changed(self, value=None, old_value=None, **kwargs):
#         "This is called when the 'acquire_busy' signal changes."

#         if self._status is None:
#             return
#         if (old_value != 0) and (value == 0):
#             # Negative-going edge means an acquisition just finished.
#             # sleep(self._delay)
#             self._status.set_finished()
#             self._status = None

#     # def arm_plan(self):
#     #     async def _wait_for_read():
#     #         future = asyncio.Future()

#     #         async def set_future_done(future):
#     #             # Checks if there is a new image being read. Stops when there is
#     #             # no new image for >  sleep_time.
#     #             status = 0
#     #             while status != 1:
#     #                 status = self.cam.acquire_busy.get()

#     #             # await asyncio.sleep(5)
#     #             future.set_result("Detector done!")

#     #         asyncio.create_task(set_future_done(future))
#     #         self._acquisition_signal.put(1, use_complete=True)
#     #         # Wait for the future to complete
#     #         await future

#     #     yield from wait_for([_wait_for_read], timeout=15)

class Trigger(TriggerBase):
    """
    This trigger mixin class takes one acquisition per trigger.
    """

    _status_type = ADTriggerStatus

    def __init__(self, *args, image_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        if image_name is None:
            image_name = "_".join([self.name, "image"])
        self._image_name = image_name
        self._acquisition_signal = self.cam.acquire
        self._acquire_busy_signal = self.cam.acquire_busy
        self._flysetup = False
        self._softsetup = False
        self._status = None
        self._delay = 0.1

    def setup_manual_trigger(self):
        # Stage signals
        self.cam.stage_sigs["trigger_mode"] = "Internal"
        self.cam.stage_sigs["num_images"] = 1
        self.cam.stage_sigs["wait_for_plugins"] = "Yes"

    def setup_external_trigger(self):
        # Stage signals
        self.cam.stage_sigs["trigger_mode"] = "TTL Veto Only"
        self.cam.stage_sigs["num_images"] = MAX_IMAGES
        self.cam.stage_sigs["wait_for_plugins"] = "No"

    # def setup_soft_trigger(self):
    #     # Stage signals
    #     self.cam.stage_sigs["trigger_mode"] = "Software + Internal"
    #     self.cam.stage_sigs["num_images"] = MAX_IMAGES
    #     self.cam.stage_sigs["wait_for_plugins"] = "Yes"
    #     self._softsetup = True

    def setup_soft_trigger(self):
        # Stage signals
        self.cam.stage_sigs["trigger_mode"] = "Software"
        self.cam.stage_sigs["num_images"] = MAX_IMAGES
        self.cam.stage_sigs["wait_for_plugins"] = "Yes"
        self.cam.stage_sigs["erase_on_start"] = "Yes"
        self._softsetup = True

    def stage(self):

        # self.cam.erase.put(1)
        # self.cam.erase.set(1).wait()

        if self._flysetup:
            self.setup_external_trigger()

        if self._softsetup:
            self.setup_soft_trigger()
            self._acquire_time = self.cam.acquire_time.get()
            self.cam.soft_trigger.put(0)

        # Make sure that detector is not armed.
        self._acquisition_signal.set(0).wait(timeout=10)
        if not self._softsetup: #TODO: find a better way to address this.
            self._acquire_busy_signal.subscribe(self._acquire_changed)

        super().stage()


        if self._flysetup or self._softsetup:
            self._acquisition_signal.set(1).wait(timeout=10)
            sleep(0.1)


    def unstage(self):
        super().unstage()
        self.cam.acquire.set(0).wait(timeout=10)
        self._flysetup = False
        if not self._softsetup:
            self._acquire_busy_signal.clear_sub(self._acquire_changed)
        self._collect_image = False
        self.setup_manual_trigger()

    def trigger(self):
        if self._staged != Staged.yes:
            raise RuntimeError(
                "This detector is not ready to trigger."
                "Call the stage() method before triggering."
            )


        # Click the Acquire_button
        self._status = self._status_type(self)
        if self._softsetup:
            self.cam.soft_trigger.put(1)
            sleep(self._acquire_time)
            self.cam.soft_trigger.put(0)
            sleep(self._delay)
            self._status.set_finished()
        else:
            self._acquisition_signal.put(1, wait=False)
        if self.hdf1.enable.get() in (True, 1, "on", "Enable"):
            self.generate_datum(self._image_name, ttime(), {})

        return self._status

    def _acquire_changed(self, value=None, old_value=None, **kwargs):
        "This is called when the 'acquire_busy' signal changes."

        if self._status is None:
            return
        if (old_value != 0) and (value == 0):
            # Negative-going edge means an acquisition just finished.
            sleep(self._delay)
            self._status.set_finished()
            self._status = None

    # def arm_plan(self):
    #     async def _wait_for_read():
    #         future = asyncio.Future()

    #         async def set_future_done(future):
    #             # Checks if there is a new image being read. Stops when there is
    #             # no new image for >  sleep_time.
    #             status = 0
    #             while status != 1:
    #                 status = self.cam.acquire_busy.get()

    #             # await asyncio.sleep(5)
    #             future.set_result("Detector done!")

    #         asyncio.create_task(set_future_done(future))
    #         self._acquisition_signal.put(1, use_complete=True)
    #         # Wait for the future to complete
    #         await future

    #     yield from wait_for([_wait_for_read], timeout=15)

class ROIStatN(Device):
    roi_name = Component(EpicsSignal, "Name", kind="config")
    use = Component(EpicsSignal, "Use", kind="config")

    max_sizex = Component(EpicsSignalRO, "MaxSizeX_RBV", kind="config")
    roi_startx = Component(EpicsSignalWithRBV, "MinY", kind="config")
    roi_sizex = Component(EpicsSignalWithRBV, "SizeY", kind="config")

    max_sizey = Component(EpicsSignalRO, "MaxSizeY_RBV", kind="config")
    roi_startxy = Component(EpicsSignalWithRBV, "MinY", kind="config")
    roi_sizey = Component(EpicsSignalWithRBV, "SizeY", kind="config")

    bdg_width = Component(EpicsSignalWithRBV, "BgdWidth", kind="config")
    min_value = Component(EpicsSignalRO, "MinValue_RBV", kind="omitted")
    max_value = Component(EpicsSignalRO, "MaxValue_RBV", kind="omitted")
    mean_value = Component(EpicsSignalRO, "MeanValue_RBV", kind="omitted")
    total_value = Component(EpicsSignalRO, "Total_RBV", kind="normal")
    net_value = Component(EpicsSignalRO, "Net_RBV", kind="omitted")

    reset_button = Component(EpicsSignal, "Reset", kind="omitted")


class TotalCorrectedSignal(SignalRO):
    """Signal that returns the deadtime corrected total counts"""

    def __init__(self, prefix, roi_index, **kwargs):
        if not roi_index:
            raise ValueError(
                "chnum must be the channel number, but "
                "f{roi_index} was passed."
            )
        self.roi_index = roi_index
        super().__init__(**kwargs)

    def get(self, **kwargs):
        value = 0
        for ch_num in range(1, self.root.num_channels + 1):
            channel = getattr(self.root, f"sca{ch_num}")
            roi = getattr(
                self.root, "stats{:d}.roi{:d}".format(ch_num, self.roi_index)
            )
            value += channel.dt_factor.get(**kwargs) * roi.total_value.get(
                **kwargs
            )
        return value
    

def _totals(attr_fix, id_range):
    defn = OrderedDict()
    for k in id_range:
        defn["{}{:d}".format(attr_fix, k)] = (
            TotalCorrectedSignal,
            "",
            {"roi_index": k, "kind": "normal"},
        )
    return defn


class VortexROIStatPlugin(ROIStatPlugin):
    _default_read_attrs = tuple(f"roi{i}" for i in range(1, MAX_ROIS + 1))

    # ROIs
    roi1 = Component(ROIStatN, "1:")
    roi2 = Component(ROIStatN, "2:")
    roi3 = Component(ROIStatN, "3:")
    roi4 = Component(ROIStatN, "4:")
    roi5 = Component(ROIStatN, "5:")
    roi6 = Component(ROIStatN, "6:")
    roi7 = Component(ROIStatN, "7:")
    roi8 = Component(ROIStatN, "8:")

    total = DynamicDeviceComponent(_totals("roi", range(1, MAX_ROIS + 1)))


class ME7Cam(CamMixin_V34, Xspress3DetectorCam):

    offset = None
    num_exposures = None
    acquire_period = None
    image_mode = None


class ME7(Trigger, DetectorBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs["_acquisition_signal"] = 0
        self.stage_sigs.popitem('cam.image_mode')

    _default_configuration_attrs = ("cam",)
    _default_read_attrs = (
        # "hdf1",
        "stats1",
        "stats2",
        "stats3",
        "stats4",
        "stats5",
        "stats6",
        "stats7",
    )

    cam = ADComponent(ME7Cam, "det1:")
    # hdf1 = ADComponent(MicHDF5, "HDF1:")

    chan1 = ADComponent(ROIPlugin, "ROI1:")
    chan2 = ADComponent(ROIPlugin, "ROI2:")
    chan3 = ADComponent(ROIPlugin, "ROI3:")
    chan4 = ADComponent(ROIPlugin, "ROI4:")
    chan5 = ADComponent(ROIPlugin, "ROI5:")
    chan6 = ADComponent(ROIPlugin, "ROI6:")
    chan7 = ADComponent(ROIPlugin, "ROI7:")

    stats1 = ADComponent(VortexROIStatPlugin, "MCA1ROI:")
    stats2 = ADComponent(VortexROIStatPlugin, "MCA2ROI:")
    stats3 = ADComponent(VortexROIStatPlugin, "MCA3ROI:")
    stats4 = ADComponent(VortexROIStatPlugin, "MCA4ROI:")
    stats5 = ADComponent(VortexROIStatPlugin, "MCA5ROI:")
    stats6 = ADComponent(VortexROIStatPlugin, "MCA6ROI:")
    stats7 = ADComponent(VortexROIStatPlugin, "MCA7ROI:")

    total = DynamicDeviceComponent(_totals("roi", range(1, MAX_ROIS + 1)))

    @property
    def read_rois(self):
        return self._read_rois

    @read_rois.setter
    def read_rois(self, rois):
        # Change total kinds
        for i in range(1, MAX_ROIS + 1):
            if i in rois:
                ktot = getattr(self.total, f"roi{i}").kind.name
                if ktot == "omitted":
                    getattr(self.total, f"roi{i}").kind = "normal"
            else:
                getattr(self.total, f"roi{i}").kind = "omitted"

        # change ROISTAT kinds
        for pixel in range(1, self.num_channels + 1):
            pix = getattr(self, f"stats{pixel}")
            for i in range(1, MAX_ROIS + 1):
                k = "normal" if i in rois else "omitted"
                getattr(pix, f"roi{i}").kind = k

        self._read_rois = list(rois)

    def select_roi(self, rois):
        for i in range(1, MAX_ROIS + 1):
            k = (
                "hinted"
                if i in rois
                else "normal" if i in self.read_rois else "omitted"
            )

            getattr(self.total, f"roi{i}").kind = k

            if k == "hinted" and i not in self.read_rois:
                self.read_rois.append(i)

    def plot_roi1(self):
        self.select_roi([1])

    def plot_roi2(self):
        self.select_roi([2])

    def plot_roi3(self):
        self.select_roi([3])

    def plot_roi4(self):
        self.select_roi([4])
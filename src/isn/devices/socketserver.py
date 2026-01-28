# from isn.devices.mic_ad_mixins import MicHDF5

# from mic_common.devices.ad_fileplugin import MicHDF5
from ophyd import ADComponent
from ophyd import DeviceStatus
from ophyd import EpicsSignal
from ophyd import EpicsSignalWithRBV
from ophyd.areadetector import DetectorBase
from ophyd.areadetector import SingleTrigger

from .mic_ad_mixins import MicHDF5

from mic_common.utils.writeDetH5 import write_det_h5
import logging
import datetime
logger = logging.getLogger(__name__)


class Trigger(SingleTrigger):
    # We can't use the ADTriggerStatus since we have no cam
    _status_type = DeviceStatus

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def trigger(self):
        self.hdf1.capture.put(1)
        super().trigger()

    # def trigger(self):
    #     #This one will always return True as it can't access a real Status signal
    #     if self._staged != Staged.yes:
    #         raise RuntimeError("This detector is not ready to trigger."
    #                            "Call the stage() method before triggering.")

    #     self._status = self._status_type(self)
    #     self.acquire.put(1, wait=False)
    #     # self._status.set_finished()
    #     return self._status

    def unstage(self):
        self.acquire.put(0)
        self.hdf1.unstage()
        super().unstage()

    # def finish_capture(self):
    #     self.acquire.put(0, wait=False)
    #     self.hdf1.capture.put(0)


class SocketServer(Trigger, DetectorBase):
    def __init__(self, *args, **kwargs):
        # We need to have a cam object to use DetectorBase without interference
        self.cam = self
        self._acquisition_signal_pv = "SG1:Acquire"
        super().__init__(*args, **kwargs)

        # Now we address the staging signals
        # self.stage_sigs.pop('cam.image_mode', None)
        # self.stage_sigs['array_counter'] = 0

        # #TODO: Fix this so that we can use them as real staging signals
        # self.hdf1.stage_sigs["num_capture"] = 50000
        self.stage_sigs = {}
        self.hdf1.stage_sigs.pop('parent.cam.array_callbacks')

    _default_configuration_attrs = None

    hdf1 = ADComponent(MicHDF5, "HDF1:")
    acquire = ADComponent(EpicsSignal, "SG1:Acquire")
    array_counter = ADComponent(EpicsSignalWithRBV, "SG1:ArrayCounter")

    def setup_flyscan_mode(self, num_lines = 50000, hdf_images = 50000):
        self.array_counter.put(0)
        self.hdf1.stage_sigs["enable"] = 1
        self.hdf1.stage_sigs["auto_save"] = 1
        self.hdf1.stage_sigs['num_capture'] = hdf_images
        self.hdf1.stage_sigs['queue_size'] = 2e5
        # self.hdf1.stage_sigs['capture'] = 1

    def write_master_h5(
        self,
        masterfile_path: str = "",
        detector_path: str = "",
        scan_name: str = "",
        det_name: str = "",
        det_file_ext: str = ".h5",
        det_key: str = "/entry",
    ):
        """
        Write master file for detector.

        Parameters:
            masterfile_path (str): Path to master HDF5 file.
            detector_path (str): Path to detector directory.
            scan_name (str): Name of the scan.
            det_name (str): Name of the detector.
            det_file_ext (str): File extension for detector files.
            det_key (str): Key for detector data in HDF5 file.
        """
        
        logger.info(
            f"{self.__class__.__name__}: Writing HDF5 file to {masterfile_path}"
        )
        logger.info(f"{self.__class__.__name__}: Detector path: {detector_path}")
        logger.info(f"{self.__class__.__name__}: Scan name: {scan_name}")

        attrs_values = {}
        attrs_values.update({"datetime": str(datetime.datetime.now())})
        # attrs_values.update({"acquire_time": self.cam.acquire_time.get()})
        # attrs_values.update({"num_images": self.cam.num_images.get()})
        # attrs_values.update({"num_frames_saved": self.cam.frame_count.get()})

        # trigger_mode = self.cam.trigger_mode.enum_strs[self.cam.trigger_mode.get()]
        # attrs_values.update({"trigger_mode": trigger_mode})

        write_det_h5(
            masterfile_path=masterfile_path,
            det_dir=detector_path,
            scan_name=scan_name,
            det_name=det_name,
            det_file_ext=det_file_ext,
            det_key=det_key,
            det_attrs_values=attrs_values,
        )

 
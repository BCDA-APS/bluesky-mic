import numpy as np
from ophyd import Component
from ophyd import EpicsSignalRO
from ophyd import TetrAMM
from ophyd.areadetector.plugins import ImagePlugin_V34
from ophyd.areadetector.plugins import StatsPlugin_V34
from ophyd.device import Staged
from ophyd.quadem import QuadEMPort

from .mic_ad_mixins import MicHDF5

from time import sleep
import datetime
import logging
from mic_common.utils.writeDetH5 import write_det_h5
logger = logging.getLogger(__name__)

TETRAMMCLOCK = 100000 #in Hz


class MyTetrAMM(TetrAMM):
    """Caen picoammeter - TetraAMM."""

    conf = Component(QuadEMPort, add_prefix="19idSFT:TetrAMM1:", port_name="QUAD_PORT")

    current1 = Component(StatsPlugin_V34, "Current1:")
    current2 = Component(StatsPlugin_V34, "Current2:")
    current3 = Component(StatsPlugin_V34, "Current3:")
    current4 = Component(StatsPlugin_V34, "Current4:")
    image = Component(ImagePlugin_V34, "image1:")
    sum_all = Component(StatsPlugin_V34, "SumAll:")

    position_y_fast = Component(EpicsSignalRO, "PositionYAve")

    hdf1 = Component(MicHDF5, "HDF1:")

    def __init__(self, *args, port_name="TetrAMM", **kwargs):
        """custom port name"""
        super().__init__(*args, **kwargs)
        self.conf.port_name.put(port_name)  # fix the port name here
        self._acquisition_signal = self.acquire
        self.stage_sigs["acquire"] = 0
        self.stage_sigs["acquire_mode"] = "Single"
        self._fast_trigger = False
        self._flysetup = False
        self._dwell_time_fraction = 0.9
        # self.setup_internal_trigger()

        # Mark some components as "config" so they do not appear on data rows.
        for attr_name in self.component_names:
            attr = getattr(self, attr_name)
            if attr_name.startswith("current_"):
                for ch_name in attr.component_names:
                    getattr(attr, ch_name).kind = "config"
            elif attr_name.startswith("position_"):
                attr.kind = "config"

        # self.sum_all.mean_value.kind = "hinted"  # Show as a data column in SPEC file.
        self.current1.mean_value.kind = "hinted"
        self.current2.mean_value.kind = "hinted"
        self.current3.mean_value.kind = "hinted"
        self.current4.mean_value.kind = "hinted"

    def setup_fast_trigger(self):
        ## This function just grabs whatever reading is available in the screen. Very fast, but not precise.""
        self.stage_sigs["acquire"] = 1
        self.stage_sigs["acquire_mode"] = "Continuous"
        self._fast_trigger = True

    def setup_internal_trigger(self):
        self.stage_sigs["acquire"] = 0
        self.stage_sigs["acquire_mode"] = "Single"
        self._fast_trigger = False

    def setup_flyscan_mode(self, num_images, acq_time, hdf_images):
        self.stage_sigs["trigger_mode"] = 2 # Ext. bulb
        self.stage_sigs["acquire_mode"] = "Multiple"
        vals_per_read = int(TETRAMMCLOCK*acq_time*self._dwell_time_fraction)
        self.stage_sigs["values_per_read"] = vals_per_read
        self.stage_sigs["num_acquire"] = num_images
        self.stage_sigs["acquire"] = 1
        self.hdf1.stage_sigs["enable"] = 1
        self.hdf1.stage_sigs["auto_save"] = 1
        self.hdf1.stage_sigs["num_capture"] = hdf_images
        self._flysetup = True


    def stage(self):
        self._status = None
        super().stage()

        if self._flysetup:
            self.acquire.set(1).wait(10)
            sleep(0.1)


    def trigger(self):
        """
        We want to operate in single mode to ensure data integrity.
        """
        if self._staged != Staged.yes:
            raise RuntimeError(
                "This detector is not ready to trigger."
                "Call the stage() method before triggering."
            )

        if self._fast_trigger:
            self._status = None
            self._status = self._status_type(self)
            self._status.set_finished()
            return self._status

        return super().trigger()

    def unstage(self):
        self._status = None
        super().unstage()

    def plot_currents(self, currents: list):
        current_dic = {
            1: self.current1.mean_value,
            2: self.current2.mean_value,
            3: self.current3.mean_value,
            4: self.current4.mean_value,
        }

        for i in np.arange(1, 5):
            if i in currents:
                current_dic[i].kind = "hinted"
            else:
                current_dic[i].kind = "normal"

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

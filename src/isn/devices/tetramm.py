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
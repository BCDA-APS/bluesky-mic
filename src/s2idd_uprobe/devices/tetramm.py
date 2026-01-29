"""
TetraMM device for controlling Caen picoammeter with NetCDF support in Bluesky workflows.

This module defines the TetraMM class, which extends ophyd.TetrAMM and provides
methods for configuring and operating the Caen picoammeter, including NetCDF file support.

.. note::
    Support exists in ophyd. Still needs NetCDF plugin support.
    See comments: https://github.com/BCDA-APS/apstools/issues/878

    ::

        from ophyd import TetrAMM

        tetramm = TetrAMM(
            "usxTetr1:qe1:",
            name="tetramm"
        )
        tetramm.wait_for_connection()

"""

from bluesky import plan_stubs as bps
from ophyd import Component, Device
from ophyd import TetrAMM
from ophyd.device import Staged
import logging

from mic_common.utils.device_utils import mode_setter
from mic_common.utils.device_utils import value_setter
from mic_common.utils.device_utils import LoggingStageSigs
from mic_common.devices.ad_fileplugin import DetHDF5
from mic_common.devices.save_data import SaveDataMic


logger = logging.getLogger(__name__)
TETRAMMCLOCK = 100000  # unit in Hz


class MicTetrAMMBase(TetrAMM):
    # """TetraMM device for controlling Caen picoammeter with NetCDF support."""

    def __init__(self, *args, **kwargs):
        """Initialize the TetraMM device and set up additional attributes."""
        super().__init__(*args, **kwargs)
        original_stage_sigs = self.stage_sigs
        self.stage_sigs = LoggingStageSigs(original_stage_sigs, prefix=self.prefix)

    def calc_values_per_read(self, dwell_time: float = None, dwell_fraction: float = 0.9):
        """Calculate the number of values per read based on the given dwell time."""
        dwell_sec = (dwell_time * dwell_fraction) / 1000
        values_per_reading = int(TETRAMMCLOCK * dwell_sec)
        return values_per_reading

    def config(
        self,
        num_pulses: int,
        dwell_time: float,
        trigger_mode: int = 1,  # 0: "Free Run", 1: "External Trigger", 2: "External Bulb", 3: "External Gate",
        acquire_mode: int = 1,  # 0: "Continuous", 1: "Multiple", 2: "Single",
        dwell_fraction: float = 0.9,
        **kwargs,
    ):
        """Configure the TetraMM device for a flyscan with the given points and dwell time."""
        values_per_reading = self.calc_values_per_read(dwell_time, dwell_fraction)

        self.stage_sigs.clear()
        self.stage_sigs["acquire"] = 0
        self.stage_sigs["acquire_mode"] = acquire_mode
        self.stage_sigs["values_per_read"] = values_per_reading
        self.stage_sigs["trigger_mode"] = trigger_mode
        self.stage_sigs["averaging_time"] = (dwell_time * dwell_fraction) / 1000
        self.stage_sigs["num_acquire"] = num_pulses




class MicTetrAMM(Device):
    cam = Component(MicTetrAMMBase, ":", kind="config", labels=("tetramm", "cam"))
    fileplugin = Component(DetHDF5, ":HDF1:", kind="config", labels=("tetramm", "fileplugin"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.fileplugin.stage_sigs.pop("parent.cam.array_callbacks", None)
            logger.info("Removing array_callbacks stage signal from TetraMM fileplugin")
        except Exception as e:
            logger.error(f"Error removing array_callbacks stage signal from TetraMM fileplugin: {e}")
            raise e

    def config_flyscan(self, num_pulses: int = None, dwell_time: float = None, **kwargs):
        """Configure the TetraMM device for a flyscan with the given points and dwell time."""
        self.unstage()
        try:
            self.cam.config(num_pulses, dwell_time, **kwargs)
        except Exception as e:
            logger.error(f"Error configuring cam for fly scan: {e}")
            raise e

        try:
            self.fileplugin.config_file_writer(num_pulses, **kwargs)
            self.fileplugin.stage_sigs.pop("parent.cam.array_callbacks", None)
        except Exception as e:
            logger.error(f"Error configuring fileplugin for fly scan: {e}")
            raise e

    def config_stepscan(self, num_pulses: int = None, dwell_time: float = None, 
                        trigger_mode: int = 0, acquire_mode: int = 2, **kwargs):
        """Configure the TetraMM device for a step scan with the given dwell time."""
        self.unstage()
        try:
            self.cam.config(num_pulses, dwell_time, trigger_mode, acquire_mode, **kwargs)
        except Exception as e:
            logger.error(f"Error configuring cam for step scan: {e}")
            raise e

    def unstage(self):
        """Unstage the TetraMM device."""
        # Check if device is already staged and unstage if necessary
        if self._staged == Staged.yes:
            logger.info("TetraMM is unstaged, unstaging ... ...")
            return super().unstage()
        elif self._staged == Staged.partially:
            logger.info("TetraMM is partially staged, unstaging cam and fileplugin separately...")
            if self.cam._staged == Staged.yes:
                self.cam.unstage()
            if self.fileplugin._staged == Staged.yes:
                self.fileplugin.unstage()

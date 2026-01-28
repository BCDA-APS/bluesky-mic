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

    # def before_flyscan(self, num_pulses, dwell_time, acquire_mode = "Multiple",
    #                    dwell_fraction = 0.9):
    #     """Configure the TetraMM device for a flyscan with the given points and dwell time."""

    #     dwell_sec = (dwell_time * dwell_fraction) / 1000
    #     values_per_reading = int(TETRAMMCLOCK * dwell_sec)
    #     logger.debug(f"dwell_time: {dwell_time}, dwell_sec: {dwell_sec}, values_per_reading: {values_per_reading}")
    #     logger.debug(f"dwell_fraction: {dwell_fraction}")

    #     yield from self.stop_acquire()
    #     yield from self.set_multiple_acquire()
    #     yield from self.set_values_per_read(values_per_reading)
    #     yield from self.set_ext_trigger()
    #     # yield from self.set_ext_bulb_trigger()
    #     yield from self.set_averaging_time(dwell_sec)
    #     yield from self.set_num_acquire(num_pulses)

    def config_flyscan(
        self,
        num_pulses: int,
        dwell_time: float,
        trigger_mode: int = 1,  # 0: "Free Run", 1: "External Trigger", 2: "External Bulb", 3: "External Gate",
        acquire_mode: int = 1,  # 0: "Continuous", 1: "Multiple", 2: "Single",
        dwell_fraction: float = 0.9,
        **kwargs,
    ):
        """Configure the TetraMM device for a flyscan with the given points and dwell time."""

        dwell_sec = (dwell_time * dwell_fraction) / 1000
        values_per_reading = int(TETRAMMCLOCK * dwell_sec)

        self.stage_sigs.clear()
        self.stage_sigs["acquire"] = 0
        self.stage_sigs["acquire_mode"] = acquire_mode
        self.stage_sigs["values_per_read"] = values_per_reading
        self.stage_sigs["trigger_mode"] = trigger_mode
        self.stage_sigs["averaging_time"] = dwell_sec
        self.stage_sigs["num_acquire"] = num_pulses

    # def stop_acquire(self):
    #     """Stop the acquire mode of the TetraMM device."""
    #     yield from self._set_acquire("Done")

    # def start_acquire(self):
    #     """Start the acquire mode of the TetraMM device."""
    #     yield from self._set_acquire("ACQUIRE")

    # def set_multiple_acquire(self):
    #     yield from self._set_acquire_mode("Multiple")

    # def set_single_acquire(self):
    #     yield from self._set_acquire_mode("Single")

    # def set_ext_trigger(self):
    #     yield from self._set_trigger_mode("EXT. TRIG.")

    # def set_int_trigger(self):
    #     yield from self._set_trigger_mode("FREE RUN")

    # def set_ext_bulb_trigger(self):
    #     yield from self._set_trigger_mode("EXT. BULB")

    # def set_ext_gate_trigger(self):
    #     yield from self._set_trigger_mode("EXT. GATE")

    # @mode_setter("acquire")
    # def _set_acquire(self, mode: str) -> None:
    #     """Set the acquire mode of the TetraMM device."""
    #     pass

    # @mode_setter("acquire_mode")
    # def _set_acquire_mode(self, mode: str) -> None:
    #     """Set the acquire mode of the TetraMM device."""
    #     pass

    # @mode_setter("trigger_mode")
    # def _set_trigger_mode(self, mode: str) -> None:
    #     """Set the trigger mode of the TetraMM device."""
    #     pass

    # @value_setter("values_per_read")
    # def set_values_per_read(self, values_per_read: int) -> None:
    #     """Set the values per read of the TetraMM device."""
    #     pass

    # @value_setter("averaging_time")
    # def set_averaging_time(self, averaging_time: float) -> None:
    #     """Set the averaging time of the TetraMM device."""
    #     pass

    # @value_setter("num_acquire")
    # def set_num_acquire(self, num_acquire: int) -> None:
    #     """Set the number of acquire of the TetraMM device."""
    #     pass


class MicTetrAMM(Device):
    cam = Component(MicTetrAMMBase, ":", kind="config", labels=("tetramm", "cam"))
    fileplugin = Component(DetHDF5, ":HDF1:", kind="config", labels=("tetramm", "fileplugin"))

    def config_flyscan(self, num_pulses: int = None, dwell_time: float = None, **kwargs):
        """Configure the TetraMM device for a flyscan with the given points and dwell time."""
        self.unstage()
        try:
            self.cam.config_flyscan(num_pulses, dwell_time, **kwargs)
        except Exception as e:
            logger.error(f"Error configuring cam for fly scan: {e}")
            raise e

        try:
            self.fileplugin.config_file_writer(num_pulses, **kwargs)
            self.fileplugin.stage_sigs.pop("parent.cam.array_callbacks", None)
        except Exception as e:
            logger.error(f"Error configuring fileplugin for fly scan: {e}")
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

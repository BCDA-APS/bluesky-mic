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
from ophyd import Component as Cpt
from ophyd import EpicsSignalWithRBV
from ophyd import TetrAMM
import logging

from mic_common.utils.device_utils import mode_setter
from mic_common.utils.device_utils import value_setter

logger = logging.getLogger(__name__)
TETRAMMCLOCK = 100000  # unit in Hz


class MicTetrAMM(TetrAMM):
    # """TetraMM device for controlling Caen picoammeter with NetCDF support."""

    # trigger_polarity = Cpt(EpicsSignalWithRBV, "TriggerPolarity")
    # fast_avg_time = Cpt(EpicsSignalWithRBV, "FastAveragingTime")
    # netcdf_enable = Cpt(EpicsSignalWithRBV, "netCDF1:EnableCallbacks")
    # file_path = Cpt(EpicsSignalWithRBV, "netCDF1:FilePath", string=True)
    # file_name = Cpt(EpicsSignalWithRBV, "netCDF1:FileName", string=True)
    # file_num = Cpt(EpicsSignalWithRBV, "netCDF1:FileNumber")
    # auto_increment = Cpt(EpicsSignalWithRBV, "netCDF1:AutoIncrement")
    # file_format = Cpt(EpicsSignalWithRBV, "netCDF1:FileTemplate", string=True)
    # file_num_capture = Cpt(EpicsSignalWithRBV, "netCDF1:NumCapture")
    # file_capture = Cpt(EpicsSignalWithRBV, "netCDF1:Capture")
    # file_write_mode = Cpt(EpicsSignalWithRBV, "netCDF1:FileWriteMode")

    def __init__(self, *args, **kwargs):
        """Initialize the TetraMM device and set up additional attributes."""
        super().__init__(*args, **kwargs)

    def before_flyscan(self, num_pulses, dwell_time, acquire_mode = "Multiple", 
                       dwell_fraction = 0.9):
        """Configure the TetraMM device for a flyscan with the given points and dwell time."""

        dwell_sec = (dwell_time * dwell_fraction) / 1000
        values_per_reading = int(TETRAMMCLOCK * dwell_sec)
        logger.debug(f"dwell_time: {dwell_time}, dwell_sec: {dwell_sec}, values_per_reading: {values_per_reading}")
        logger.debug(f"dwell_fraction: {dwell_fraction}")
        
        yield from self.stop_acquire()
        yield from self.set_multiple_acquire()
        yield from self.set_values_per_read(values_per_reading)
        yield from self.set_ext_trigger()
        # yield from self.set_ext_bulb_trigger()
        yield from self.set_averaging_time(dwell_sec)
        yield from self.set_num_acquire(num_pulses)


    def stop_acquire(self):
        """Stop the acquire mode of the TetraMM device."""
        yield from self._set_acquire("Done")

    def start_acquire(self):
        """Start the acquire mode of the TetraMM device."""
        yield from self._set_acquire("ACQUIRE")

    def set_multiple_acquire(self):
        yield from self._set_acquire_mode("Multiple")

    def set_ext_trigger(self):
        yield from self._set_trigger_mode("EXT. TRIG.")

    def set_int_trigger(self):
        yield from self._set_trigger_mode("FREE RUN")

    def set_ext_bulb_trigger(self):
        yield from self._set_trigger_mode("EXT. BULB")

    def set_ext_gate_trigger(self):
        yield from self._set_trigger_mode("EXT. GATE")


    @mode_setter("acquire")
    def _set_acquire(self, mode: str) -> None:
        """Set the acquire mode of the TetraMM device."""
        pass
    
    
    @mode_setter("acquire_mode")
    def _set_acquire_mode(self, mode: str) -> None:
        """Set the acquire mode of the TetraMM device."""
        pass


    @mode_setter("trigger_mode")
    def _set_trigger_mode(self, mode: str) -> None:
        """Set the trigger mode of the TetraMM device."""
        pass


    @value_setter("values_per_read")
    def set_values_per_read(self, values_per_read: int) -> None:
        """Set the values per read of the TetraMM device."""
        pass

    @value_setter("averaging_time")
    def set_averaging_time(self, averaging_time: float) -> None:
        """Set the averaging time of the TetraMM device."""
        pass

    @value_setter("num_acquire")
    def set_num_acquire(self, num_acquire: int) -> None:
        """Set the number of acquire of the TetraMM device."""
        pass



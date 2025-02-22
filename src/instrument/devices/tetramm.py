"""
TetrAMM, Caen picoammeter.

.. note:  Support exists in ophyd.  Still needs NetCDF plugin support.
    See comments: https://github.com/BCDA-APS/apstools/issues/878

    ::

        from ophyd import TetrAMM

        tetramm = TetrAMM("usxTetr1:qe1:", name="tetramm")
        tetramm.wait_for_connection()

"""

from bluesky import plan_stubs as bps
from ophyd import Component as Cpt
from ophyd import Device
from ophyd import EpicsSignal, EpicsSignalWithRBV
from ophyd import TetrAMM

TETRAMMCLOCK = 100000  # unit in Hz


class S19TetraMM(TetrAMM):

    trigger_polarity = Cpt(EpicsSignalWithRBV, "TriggerPolarity")
    fast_avg_time = Cpt(EpicsSignalWithRBV, "FastAveragingTime")
    netcdf_enable = Cpt(EpicsSignalWithRBV, "netCDF1:EnableCallbacks")
    file_path = Cpt(EpicsSignalWithRBV, "netCDF1:FilePath", string=True)
    file_name = Cpt(EpicsSignalWithRBV, "netCDF1:FileName", string=True)
    file_num = Cpt(EpicsSignalWithRBV, "netCDF1:FileNumber")
    auto_increment = Cpt(EpicsSignalWithRBV, "netCDF1:AutoIncrement")
    file_format = Cpt(EpicsSignalWithRBV, "netCDF1:FileTemplate", string=True)
    file_num_capture = Cpt(EpicsSignalWithRBV, "netCDF1:NumCapture")
    file_capture = Cpt(EpicsSignalWithRBV, "netCDF1:Capture")
    file_write_mode = Cpt(EpicsSignalWithRBV, "netCDF1:FileWriteMode")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.range = self.em_range
        self.avg_time = self.averaging_time

    def initialization(self):
        yield from bps.mv(
            self.acquire_mode,
            1,  # acquire_mode set to Multiple
            self.range,
            0,  # Range set to +/- 120 uA
            self.num_channels,
            2,  # Num of channel set to 4
            self.trigger_mode,
            1,  # Trigger mode set to Ext. trig
            self.trigger_polarity,
            0,  # Trigger polarity set to Positive
            self.bias_state,
            0,  # Bias state set to Off
            self.bias_voltage,
            0,  # Bias voltage set to 0V
            self.bias_interlock,
            0,  # Bias interlock set to off
        )

        yield from bps.mv(
            self.file_write_mode,
            2,  # NetCDF file write mode to Strea
            self.file_format,
            f"%s%s_%05d.nc",  # Set default NetCDF file formatter
            self.file_name,
            f"19ide_",  # Set it up for ISN (19ide)
        )

    def setup_scan(self, pts, dwell):
        values_per_reading = int(TETRAMMCLOCK * dwell - 1)
        yield from bps.mv(
            self.avg_time,
            dwell,
            self.values_per_read,
            values_per_reading,
            self.num_acquire,
            pts,
        )
        yield from bps.mv(self.file_num_capture, pts)

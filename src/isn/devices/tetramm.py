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
from ophyd import EpicsSignalWithRBV, EpicsSignalRO

from ophyd.areadetector import (
    TriggerBase,
    DetectorBase,
)

from ophyd.status import DeviceStatus
from time import sleep
from apstools.utils import run_in_thread

TETRAMMCLOCK = 100000  # unit in Hz




class Trigger(TriggerBase):

    _status_type = DeviceStatus


    def stage(self):
        '''Staging detector. Must ensure that stage signals are well defined previously.'''

        # self.acquire.set(0).wait(timeout=10)
        # self.acquire_mode.set('Single').wait(timeout=10) 
        # self.acquisitions.set(1).wait(timeout=10)
        self._staged = True


    def trigger(self):
        if not self._staged:
            raise RuntimeError("This detector is not ready to trigger."
                               "Call the stage() method before triggering.")
        
        @run_in_thread
        def delay(status_obj):
            avg_time = self.averaging_time.get()
            sleep(avg_time+0.1)
            status_obj.set_finished()

        self._status = self._status_type(self)
        self.acquire.set(1).wait(timeout=10)
        delay(self._status)
        return self._status

    def unstage(self):
        # self.acquire.set(0).wait(timeout=10)
        self._staged = False

class TetrammDetector(DetectorBase):

    _default_configuration_attrs = tuple(attr for attr in DetectorBase._default_configuration_attrs if attr not in ['cam'])
    _default_read_attrs = ['current_1']


class TetraMM(Trigger, TetrammDetector):



    #Trigger configs
    acquisitions = Cpt(EpicsSignalWithRBV, ":NumAcquire", name='acquisitions', kind='config')
    trigger_polarity = Cpt(EpicsSignalWithRBV, ":TriggerPolarity", name='trigger_polarity', kind='config')
    fast_avg_time = Cpt(EpicsSignalWithRBV, ":FastAveragingTime")

    acquire = Cpt(EpicsSignalWithRBV, ":Acquire", name='acquisitions', kind='config')
    acquire_mode = Cpt(EpicsSignalWithRBV, ":AcquireMode", name='acquire_mode', kind='config')
    averaging_time = Cpt(EpicsSignalWithRBV, ":AveragingTime", name='averaging_time', kind='config')

    
    #File configs
    netcdf_enable = Cpt(EpicsSignalWithRBV, ":netCDF1:EnableCallbacks")
    file_path = Cpt(EpicsSignalWithRBV, ":netCDF1:FilePath", string=True)
    file_name = Cpt(EpicsSignalWithRBV, ":netCDF1:FileName", string=True)
    file_num = Cpt(EpicsSignalWithRBV, ":netCDF1:FileNumber")
    auto_increment = Cpt(EpicsSignalWithRBV, ":netCDF1:AutoIncrement")
    file_format = Cpt(EpicsSignalWithRBV, ":netCDF1:FileTemplate", string=True)
    file_num_capture = Cpt(EpicsSignalWithRBV, ":netCDF1:NumCapture")
    file_capture = Cpt(EpicsSignalWithRBV, ":netCDF1:Capture")
    file_write_mode = Cpt(EpicsSignalWithRBV, ":netCDF1:FileWriteMode")

    current_1 = Cpt(EpicsSignalRO, ":Current1:MeanValue_RBV", name='current_1', kind='hinted')
    current_2 = Cpt(EpicsSignalRO, ":Current2:MeanValue_RBV", name='current_2', kind='hinted')
    current_3 = Cpt(EpicsSignalRO, ":Current3:MeanValue_RBV", name='current_3', kind='hinted')


    # def initialization(self):
    #     yield from bps.mv(
    #         self.acquire_mode,
    #         1,  # acquire_mode set to Multiple
    #         self.range,
    #         0,  # Range set to +/- 120 uA
    #         self.num_channels,
    #         2,  # Num of channel set to 4
    #         self.trigger_mode,
    #         1,  # Trigger mode set to Ext. trig
    #         self.trigger_polarity,
    #         0,  # Trigger polarity set to Positive
    #         self.bias_state,
    #         0,  # Bias state set to Off
    #         self.bias_voltage,
    #         0,  # Bias voltage set to 0V
    #         self.bias_interlock,
    #         0,  # Bias interlock set to off
    #     )

    #     yield from bps.mv(
    #         self.file_write_mode,
    #         2,  # NetCDF file write mode to Strea
    #         self.file_format,
    #         f"%s%s_%05d.nc",  # Set default NetCDF file formatter
    #         self.file_name,
    #         f"19ide_",  # Set it up for ISN (19ide)
    #     )

    # def setup_scan(self, pts, dwell):
    #     values_per_reading = int(TETRAMMCLOCK * dwell - 1)
    #     yield from bps.mv(
    #         self.avg_time,
    #         dwell,
    #         self.values_per_read,
    #         values_per_reading,
    #         self.num_acquire,
    #         pts,
    #     )
    #     yield from bps.mv(self.file_num_capture, pts)
import logging
import time as ttime
import numpy as np

from ophyd import Component
from ophyd import EpicsSignalRO
from ophyd import TetrAMM
from ophyd.areadetector.plugins import ImagePlugin_V34
from ophyd.areadetector.plugins import StatsPlugin_V34
from ophyd.device import Staged
from ophyd.quadem import QuadEMPort

from ophyd.status import DeviceStatus

from apstools.utils import run_in_thread

logger = logging.getLogger(__name__)
logger.info(__file__)


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

    def __init__(self, *args, port_name="TetrAMM", **kwargs):
        """custom port name"""
        super().__init__(*args, **kwargs)
        self.conf.port_name.put(port_name)  # fix the port name here
        self._acquisition_signal = self.acquire
        self.stage_sigs["acquire"] = 0
        self.stage_sigs["acquire_mode"] = "Single"

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


    def stage(self):
        self._status = None
        super().stage()

    def trigger(self):
        """
        We want to operate in single mode to ensure data integrity.
        """
        if self._staged != Staged.yes:
            raise RuntimeError(
                "This detector is not ready to trigger."
                "Call the stage() method before triggering."
            )

        self._status = None
        self._acquisition_signal.put(1, wait=True)
        self._status = self._status_type(self)
        self._status.set_finished()
        return self._status
    
    def unstage(self):
        self._status = None
        super().unstage()
    

    def measure_currents(self, currents: list):
        current_dic = {1: self.current1.mean_value,
                       2: self.current2.mean_value,
                       3: self.current3.mean_value,
                       4: self.current4.mean_value}
        
        for i in np.arange(1, 5):
            if i in currents:
                current_dic[i].kind = 'hinted'
            else:
                current_dic[i].kind = 'normal'


    
    






























"""
TetrAMM, Caen picoammeter.

.. note:  Support exists in ophyd.  Still needs NetCDF plugin support.
    See comments: https://github.com/BCDA-APS/apstools/issues/878

    ::

        from ophyd import TetrAMM

        tetramm = TetrAMM("usxTetr1:qe1:", name="tetramm")
        tetramm.wait_for_connection()

"""

# from ophyd import Component as Cpt
# from ophyd import EpicsSignalWithRBV, EpicsSignalRO
# from ophyd import TetrAMM

# import logging
# import time as ttime

# from ophyd import Component
# from ophyd import TetrAMM
# from ophyd.areadetector.plugins import ImagePlugin_V34
# from ophyd.areadetector.plugins import StatsPlugin_V34
# from ophyd.quadem import QuadEMPort


# from ophyd.areadetector import (
#     TriggerBase,
#     DetectorBase,
# )

# from ophyd.status import DeviceStatus
# from time import sleep
# from apstools.utils import run_in_thread

# TETRAMMCLOCK = 100000  # unit in Hz




# class Trigger(TriggerBase):

#     def stage(self):
#         '''Staging detector. Must ensure that stage signals are well defined previously.'''
#         self.acquire.put(0, timeout=10)
#         self.acquire_mode.put('Single', wait=True, timeout=10)
#         # self.acquisitions.put(100, wait=True, timeout=10) 
#         print("Succesfully staged.")
#         self._staged = True


#     def trigger(self):
#         if not self._staged:
#             raise RuntimeError("This detector is not ready to trigger."
#                                "Call the stage() method before triggering.")

#         _status = DeviceStatus(self)
#         print("about to trigger")
#         self.acquire.put(1, wait=False, timeout=10)
#         print("triggered")
#         sleep(0.1)
#         print("slept")
#         _status.set_finished()
#         return _status

#     def unstage(self):
#         self.acquire.put(0, timeout=10)
#         self.acquire_mode.put('Continuous', wait=True, timeout=10)
#         self.acquire.put(1, timeout=10)
#         self._staged = False

# class TetrammDetector(DetectorBase):

#     _default_configuration_attrs = tuple(attr for attr in DetectorBase._default_configuration_attrs if attr not in ['cam'])
#     _default_read_attrs = ['current_1']


# class XPCS_TetrAMM(TetrAMM):
#     """Caen picoammeter - TetraAMM."""

#     conf = Component(QuadEMPort, add_prefix="19idSFT:TetrAMM1:", port_name="QUAD_PORT")

#     current1 = Component(StatsPlugin_V34, "Current1:")
#     current2 = Component(StatsPlugin_V34, "Current2:")
#     current3 = Component(StatsPlugin_V34, "Current3:")
#     current4 = Component(StatsPlugin_V34, "Current4:")
#     image = Component(ImagePlugin_V34, "image1:")
#     sum_all = Component(StatsPlugin_V34, "SumAll:")

#     def __init__(self, *args, port_name="TetrAMM", **kwargs):
#         """custom port name"""
#         super().__init__(*args, **kwargs)
#         self.conf.port_name.put(port_name)  # fix the port name here
#         self.stage_sigs = {}

#         # Mark some components as "config" so they do not appear on data rows.
#         for attr_name in self.component_names:
#             attr = getattr(self, attr_name)
#             if attr_name.startswith("current_"):
#                 for ch_name in attr.component_names:
#                     getattr(attr, ch_name).kind = "config"
#             elif attr_name.startswith("position_"):
#                 attr.kind = "config"

#         self.sum_all.mean_value.kind = "hinted"  # Show as a data column in SPEC file.
#         self.current1.mean_value.kind = "hinted"
#         self.current2.mean_value.kind = "hinted"
#         self.current3.mean_value.kind = "hinted"
#         self.current4.mean_value.kind = "hinted"



# class MyTetrAMM(Trigger, XPCS_TetrAMM):

#     pass


    # #Trigger configs
    # acquisitions = Cpt(EpicsSignalWithRBV, "NumAcquire", name='acquisitions', kind='config')
    # trigger_polarity = Cpt(EpicsSignalWithRBV, "TriggerPolarity", name='trigger_polarity', kind='config')
    # fast_avg_time = Cpt(EpicsSignalWithRBV, "FastAveragingTime")

    # acquire = Cpt(EpicsSignalWithRBV, "Acquire", name='acquisitions', kind='config')
    # acquire_mode = Cpt(EpicsSignalWithRBV, "AcquireMode", name='acquire_mode', kind='config')
    # averaging_time = Cpt(EpicsSignalWithRBV, "AveragingTime", name='averaging_time', kind='config')
    # sample_time = Cpt(EpicsSignalRO, "SampleTime_RBV", name="sample_time")

    
    # #File configs
    # netcdf_enable = Cpt(EpicsSignalWithRBV, ":netCDF1:EnableCallbacks")
    # file_path = Cpt(EpicsSignalWithRBV, ":netCDF1:FilePath", string=True)
    # file_name = Cpt(EpicsSignalWithRBV, ":netCDF1:FileName", string=True)
    # file_num = Cpt(EpicsSignalWithRBV, ":netCDF1:FileNumber")
    # auto_increment = Cpt(EpicsSignalWithRBV, ":netCDF1:AutoIncrement")
    # file_format = Cpt(EpicsSignalWithRBV, ":netCDF1:FileTemplate", string=True)
    # file_num_capture = Cpt(EpicsSignalWithRBV, ":netCDF1:NumCapture")
    # file_capture = Cpt(EpicsSignalWithRBV, ":netCDF1:Capture")
    # file_write_mode = Cpt(EpicsSignalWithRBV, ":netCDF1:FileWriteMode")

    # current_1 = Cpt(EpicsSignalRO, ":Current1:MeanValue_RBV", name='current_1', kind='hinted')
    # current_2 = Cpt(EpicsSignalRO, ":Current2:MeanValue_RBV", name='current_2', kind='hinted')
    # current_3 = Cpt(EpicsSignalRO, ":Current3:MeanValue_RBV", name='current_3', kind='hinted')


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
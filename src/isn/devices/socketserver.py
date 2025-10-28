from ophyd import (
    ADComponent,
    EpicsSignal,
    DeviceStatus,
    EpicsSignalWithRBV
)

from ophyd.areadetector import (
    SingleTrigger,
    DetectorBase,
    Staged
)

from apstools.utils import run_in_thread
from mic_common.devices.ad_fileplugin import DetHDF5
from mic_common.devices.ad_fileplugin import MicHDF5
# from isn.devices.mic_ad_mixins import MicHDF5
from time import sleep

from collections import OrderedDict

class Trigger(SingleTrigger):

    # We can't use the ADTriggerStatus since we have no cam
    _status_type = DeviceStatus
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


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
        #We need to have a cam object to use DetectorBase without interference
        self.cam = self
        self._acquisition_signal_pv = "SG1:Acquire"
        super().__init__(*args, **kwargs)

        #Now we address the staging signals
        # self.stage_sigs.pop('cam.image_mode', None)
        # self.stage_sigs['array_counter'] = 0

        # #TODO: Fix this so that we can use them as real staging signals
        # self.hdf1.stage_sigs["num_capture"] = 50000
        self.stage_sigs = {}
        

    _default_configuration_attrs = None

    hdf1 = ADComponent(MicHDF5, 'HDF1:')

    acquire = ADComponent(EpicsSignal, "SG1:Acquire")
    array_counter = ADComponent(EpicsSignalWithRBV, "SG1:ArrayCounter")
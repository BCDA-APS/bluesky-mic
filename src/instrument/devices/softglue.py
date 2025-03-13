from ophyd import Device
from ophyd import EpicsSignal, EpicsSignalWithRBV
from ophyd import Component
from epics import caput

class MyEpicsSignal(EpicsSignal):
    
    def set(self, value):
        caput(self.pvname, str(value))

class SoftGlue(Device):

    n_pts = Component(MyEpicsSignal, "DivByN-4_N")
    enable = Component(MyEpicsSignal, "BUFFER-4_IN_Signal")


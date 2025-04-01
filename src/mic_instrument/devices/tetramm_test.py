from ophyd import Device, EpicsSignalRO, Component

class Tetramm(Device):
    current_1 = Component(EpicsSignalRO, ':Current1:MeanValue_RBV', name='current_1', kind='hinted')

from ophyd import Device, EpicsSignalRO, Component

class Tetramm(Device):
    current_1 = Component(EpicsSignalRO, 'Current1:MeanValue_RBV', name='current_1')

tetramm_1 = Tetramm('19idSFT:TetrAMM1:', name='tetramm_1')
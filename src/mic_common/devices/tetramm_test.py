"""Test module for TetrAMM device."""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignalRO


class Tetramm(Device):
    """Test device for TetrAMM current measurements."""

    current_1 = Component(
        EpicsSignalRO, ":Current1:MeanValue_RBV", name="current_1", kind="hinted"
    )

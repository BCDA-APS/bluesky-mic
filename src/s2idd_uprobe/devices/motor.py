"""
Modify the motor ophyd motor device to add additional fields.

@author: yluo(grace227)


"""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal

class Motor(Device):
    """
    Motor device for controlling motor in Bluesky workflows.
    """

    pass
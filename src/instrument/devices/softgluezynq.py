'''
Softglue implementation for ISN
'''

from ophyd import Component, Device, EpicsSignal, EpicsSignalRO
from collections import OrderedDict
from bluesky.plan_stubs import mv #noqa


def SoftGlueSignal(Device):
    

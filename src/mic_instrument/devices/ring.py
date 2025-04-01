'''Device that reads the current of the storage ring.'''

from ophyd import Device, Component, EpicsSignalRO

class Ring(Device):
    current = Component(EpicsSignalRO, ':CurrentM', kind='config')



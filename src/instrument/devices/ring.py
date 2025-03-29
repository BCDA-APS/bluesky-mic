'''Device that reads the current of the storage ring.'''

__all__ = ['ring']

from ophyd import Device, Component, EpicsSignalRO

class Ring(Device):
    current = Component(EpicsSignalRO, 'CurrentM', kind='config')

ring = Ring('S-DCCT:', name='ring', labels=('ring',))


"""Device that reads the current of the storage ring."""

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignalRO


class Ring(Device):
    """Device for reading storage ring current."""

    current = Component(EpicsSignalRO, ":CurrentM", kind="config")

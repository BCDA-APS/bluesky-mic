"""
APS filter adapted from POLAR
"""

import numpy as np

from ophyd import (
    Component,
    DynamicDeviceComponent,
    Device,
    EpicsSignal,
    EpicsSignalRO,
)

NUM_FILTERS = 8


class FilterSlot(Device):
    status = Component(EpicsSignal, "Set", string=True, labels=("baseline",))
    lock = Component(EpicsSignal, "Lock", string=True)
    material = Component(EpicsSignal, "Material", string=True)
    thickness = Component(EpicsSignal, "Thickness")
    enable = Component(EpicsSignal, "Enable", string=True)
    transmission = Component(EpicsSignalRO, "Transmission")


def make_filter_slots(num: int):
    defn = {}
    for n in range(1, num + 1):
        defn[f"f{n}"] = (FilterSlot, f"Fi{n}:", dict(kind="config"))
    return defn


class APSFilter(Device):

    # Status and information

    energy_select = Component(
        EpicsSignal, "EnergySelect", string=True, kind="config"
    )
    mono_energy = Component(EpicsSignalRO, "EnergyBeamline", kind="config")
    local_energy = Component(EpicsSignal, "EnergyLocal", kind="config")

    status = Component(EpicsSignalRO, "Status", string=True, kind="config")

    transmission_readback = Component(EpicsSignalRO, "Transmission", labels=("baseline",))
    transmission_setpoint = Component(
        EpicsSignal, "TransmissionSetpoint", kind="config"
    )
    transmission_factor = Component(
        EpicsSignal, "TransmissionFactor", kind="config"
    )

    mask_readback = Component(EpicsSignalRO, "FilterMask", kind="config")
    mask_setpoint = Component(
        EpicsSignal, "FilterMaskSetpoint", kind="config"
    )

    message = Component(EpicsSignalRO, "Message", kind="config")

    slots = DynamicDeviceComponent(make_filter_slots(NUM_FILTERS))

    # Configuration
    wait_time = Component(EpicsSignal, "WaitTime", kind="config")
    debug_level = Component(EpicsSignal, "Debug", kind="config")


    def put_in(self, list_of_slots: list[int]|int):
        """Put in the specified filter slots. Does not remove any existing filters.

        Parameters:
            list_of_slots (list of int): List of filter slot numbers to put in.
        """
        if not isinstance(list_of_slots, list):
            list_of_slots = [list_of_slots]
        for i in list_of_slots:
            if i < 1 or i > NUM_FILTERS:
                raise ValueError(f"Invalid filter slot number: {i}")
            slot = getattr(self.slots, f"f{i}")
            slot.status.set(1).wait()


    def put_out(self, list_of_slots: list[int]|int):
        """Put out the specified filter slots. Does not remove any existing filters.

        Parameters:
            list_of_slots (list of int): List of filter slot numbers to put out.
        """
        if not isinstance(list_of_slots, list):
            list_of_slots = [list_of_slots]
        for i in list_of_slots:
            if i < 1 or i > NUM_FILTERS:
                raise ValueError(f"Invalid filter slot number: {i}")
            slot = getattr(self.slots, f"f{i}")
            slot.status.set(0).wait()

    def filters_in(self, list_of_slots: list[int]|int):
        """Puts in the specified filter slots and removes any filters not in the list."""

        if not isinstance(list_of_slots, list):
            list_of_slots = [list_of_slots]
        mask_value = np.sum([2 ** (i - 1) for i in list_of_slots])
        self.mask_setpoint.set(mask_value).wait()
        self.mask_setpoint.set(mask_value).wait() #Double to address the EPICS issue where the first set may not take effect.
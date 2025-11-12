from ophyd import Device
from ophyd import Component
from ophyd import EpicsSignalRO

class HutchTemp(Device):

    kb = Component(EpicsSignalRO, "SensorATempM")
    granite = Component(EpicsSignalRO, "SensorBTempM")
    floor = Component(EpicsSignalRO, "SensorCTempM")
    se_wall = Component(EpicsSignalRO, "SensorDTempM")
    nw_wall = Component(EpicsSignalRO, "SensorETempM")

    
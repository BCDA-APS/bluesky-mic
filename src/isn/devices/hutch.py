from ophyd import Device
from ophyd import Component
from ophyd import EpicsSignalRO
from ophyd import Status

from ophyd.areadetector import SingleTrigger

# class Trigger(SingleTrigger):
    # def stage(self):
    #     pass

    # def trigger(self):
    #     st = Status(self)
    #     st.set_finished()
    #     return st

    # def unstage(self):
    #     pass

class HutchTemp(Device):

    # _default_read_attrs = (
    #     "kb",
    #     "granite",
    #     "floor",
    #     "se_wall",
    #     "nw_wall",
    # )

    kb = Component(EpicsSignalRO, "SensorATempM")
    granite = Component(EpicsSignalRO, "SensorBTempM")
    floor = Component(EpicsSignalRO, "SensorCTempM")
    se_wall = Component(EpicsSignalRO, "SensorDTempM")
    nw_wall = Component(EpicsSignalRO, "SensorETempM")

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)


    
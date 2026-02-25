from s8bmb_uprobe.devices.motor import Motor
from ophyd import Component, Device, EpicsSignal


class Sample(Device):
    x = Component(Motor, ":m27", kind="config", labels=("motor", "samx"))
    y = Component(Motor, ":m10", kind="config", labels=("motor", "samy"))
    # z = Component(Motor, ":m36", kind="config", labels=("motor", "samz"))

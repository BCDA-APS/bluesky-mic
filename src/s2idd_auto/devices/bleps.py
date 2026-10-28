"""Ophyd object for BLEPS (beamline equipment protection system) device."""

from ophyd import Component, Device, EpicsSignal
import logging

logger = logging.getLogger(__name__)

class BLEPSTemp(Device):
    """BLEPS temperature device for monitoring the temperature of the beamline equipment protection system in Bluesky workflows."""

    setpoint = Component(EpicsSignal, "_SET_POINT", kind="config", labels=("bleps", "temp-setpoint"))
    readback = Component(EpicsSignal, "_CURRENT", kind="config", labels=("bleps", "temp-readback"))


class BLEPS2ID(Device):
    """BLEPS device for controlling the beamline equipment protection system in Bluesky workflows."""

    temp1 = Component(BLEPSTemp, ":BLEPS:TEMP1", kind="config", labels=("bleps", "temp1"))
    temp2 = Component(BLEPSTemp, ":BLEPS:TEMP2", kind="config", labels=("bleps", "temp2"))
    temp3 = Component(BLEPSTemp, ":BLEPS:TEMP3", kind="config", labels=("bleps", "temp3"))
    temp4 = Component(BLEPSTemp, ":BLEPS:TEMP4", kind="config", labels=("bleps", "temp4"))
    temp5 = Component(BLEPSTemp, ":BLEPS:TEMP5", kind="config", labels=("bleps", "temp5"))
    temp6 = Component(BLEPSTemp, ":BLEPS:TEMP6", kind="config", labels=("bleps", "temp6"))
    temp7 = Component(BLEPSTemp, ":BLEPS:TEMP7", kind="config", labels=("bleps", "temp7"))
    temp8 = Component(BLEPSTemp, ":BLEPS:TEMP8", kind="config", labels=("bleps", "temp8"))
    temp9 = Component(BLEPSTemp, ":BLEPS:TEMP9", kind="config", labels=("bleps", "temp9"))
    temp10 = Component(BLEPSTemp, ":BLEPS:TEMP10", kind="config", labels=("bleps", "temp10"))
    temp11 = Component(BLEPSTemp, ":BLEPS:TEMP11", kind="config", labels=("bleps", "temp11"))
    temp12 = Component(BLEPSTemp, ":BLEPS:TEMP12", kind="config", labels=("bleps", "temp12"))
    temp13 = Component(BLEPSTemp, ":BLEPS:TEMP13", kind="config", labels=("bleps", "temp13"))
    temp14 = Component(BLEPSTemp, ":BLEPS:TEMP14", kind="config", labels=("bleps", "temp14"))
    temp15 = Component(BLEPSTemp, ":BLEPS:TEMP15", kind="config", labels=("bleps", "temp15"))
    temp16 = Component(BLEPSTemp, ":BLEPS:TEMP16", kind="config", labels=("bleps", "temp16"))
    temp17 = Component(BLEPSTemp, ":BLEPS:TEMP17", kind="config", labels=("bleps", "temp17"))
    temp18 = Component(BLEPSTemp, ":BLEPS:TEMP18", kind="config", labels=("bleps", "temp18"))


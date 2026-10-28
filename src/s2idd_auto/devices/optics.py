"""Optics device module for Bluesky workflows."""

from ophyd import Component, Device
from s2idd_uprobe.devices.motor import Motor
import logging

logger = logging.getLogger(__name__)

class UpstreamMirror(Device):
    """Upstream mirror device for controlling the M1 motors in Bluesky workflows."""

    x = Component(Motor, ":m1", kind="config", labels=("motor", "m1-x"))
    y = Component(Motor, ":m2", kind="config", labels=("motor", "m1-y"))
    pitch = Component(Motor, ":m3", kind="config", labels=("motor", "m1-pitch"))

class MonoMotors(Device):
    """Monochromator motors device for controlling the monochromator motors in Bluesky workflows."""

    bragg = Component(Motor, ":m17", kind="config", labels=("motor", "mono-bragg"))
    pitch = Component(Motor, ":m18", kind="config", labels=("motor", "mono-pitch"))
    roll = Component(Motor, ":m19", kind="config", labels=("motor", "mono-roll"))
    gap = Component(Motor, ":m20", kind="config", labels=("motor", "mono-gap"))

class UpstreamPinhole(Device):
    """Upstream pinhole device for controlling the upstream pinhole motor in Bluesky workflows."""

    x = Component(Motor, ":m31", kind="config", labels=("motor", "uspinhole-x"))
    y = Component(Motor, ":m30", kind="config", labels=("motor", "uspinhole-y"))

class OSA(Device):
    """OSA device for controlling the OSA motor in Bluesky workflows."""

    x = Component(Motor, ":m11", kind="config", labels=("motor", "osa-x"))
    y = Component(Motor, ":m12", kind="config", labels=("motor", "osa-y"))


"""Optics device module for Bluesky workflows.

This module provides classes for controlling beamline optics devices.
"""

from ophyd import Component
from ophyd import Device
from s2idd_uprobe.devices.motor import Motor

# Compatibility name for user code that imported the old class location.
from mic_common.devices.optics import Mono2ID

KohzuMono = Mono2ID


class OSA(Device):
    """OSA device for controlling the OSA motor in Bluesky workflows."""

    x = Component(Motor, ":m11", kind="config", labels=("motor", "osax"))
    y = Component(Motor, ":m12", kind="config", labels=("motor", "osay"))

"""
Add more attributes to the ophyd.EpicsMotor device.

@author: yluo(grace227)


"""

from ophyd import Component
from ophyd import EpicsMotor
from ophyd import EpicsSignal

import logging
logger = logging.getLogger(__name__)

class Motor(EpicsMotor):
    """
    Motor class inherits from ophyd.EpicsMotor to add additional attributes.
    """

    max_velocity = Component(EpicsSignal, ".VMAX")
    resolution = Component(EpicsSignal, ".MRES")
    scan_speed: float = None
    
    def set_speed(self, speed: float = None):
        if speed is None:
            speed = self.get_max_velocity()
            logger.info(f"Scan speed is not set, using max velocity: {speed}")
        self.velocity.put(speed)
    
    def get_max_velocity(self):
        return self.max_velocity.get()

    def get_resolution(self):
        return self.resolution.get()

    def calculate_scan_speed(self, stepsize, dwell):
        return stepsize / (dwell / 1000)

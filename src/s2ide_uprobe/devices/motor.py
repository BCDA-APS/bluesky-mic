"""
Custom motor class for s2IDE beamline.

@author: yluo(grace227)


"""

from ophyd import Component
from ophyd import EpicsMotor
from ophyd import EpicsSignal

MAX_RETRIES = 5


class Motor(EpicsMotor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _move_changed(self):
        return self.max_velocity.get()

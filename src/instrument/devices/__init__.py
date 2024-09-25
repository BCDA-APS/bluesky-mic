"""
Custom Device Definitions & Instatiation
"""

## Simulated detector/motor
from .simulated_1d_detector import sim_1d  # noqa: F401
from .simulated_1d_detector import sim_motor  # noqa: F401
from .motors import *
from .PositionerStream import postrm, setup_positionstream
from .ProfileMove import pm1, setup_profile_move
from .SaveData import savedata, setup_savedata
from .ScanRecord import scan1, scan2, setup_scanrecord
from .SoftglueZynq import sgz, setup_softgluezynq
from .TetraMM import tmm, setup_tetramm
from .Xspress3 import xp3, setup_xspress3
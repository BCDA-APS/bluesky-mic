"""
Custom Device Definitions & Instatiation
"""

# ## Simulated detector/motor
# from .simulated_1d_detector import sim_1d  # noqa: F401
# from .simulated_1d_detector import sim_motor  # noqa: F401
# from .motors import *
from .positioner_stream import postrm, setup_positionstream
from .profile_move import pm1
from .save_data import savedata
from .scan_record import scan1, scan2, setup_scanrecord
from .softglue_zynq import sgz, setup_softgluezynq
from .tetramm import tmm, setup_tetramm
from .xspress3 import xp3, setup_xspress3
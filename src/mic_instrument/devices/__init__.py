"""Ophyd-style devices."""

from .ad_fileplugin import DetHDF5  # noqa: F401
from .ad_fileplugin import DetNetCDF  #noqa: F401
from .bda import BDA  # noqa: F401

# from .scan_record import scan1, scan2
# from .positioner_stream import postrm  # noqa: F401
# from .profile_move import pm1  # noqa: F401
# from .softglue_zynq import sgz  # noqa: F401
from .eiger1m import Eiger1M  # noqa: F401

# Temporary way to load useful devices automatically
from .hhl_mirrors import HHL_Mirrors  # noqa: F401
from .my_motor_bundle import MyMotorBundle  # noqa: F401
from .ring import Ring  # noqa: F401
from .save_data import SaveDataMic  # noqa: F401
from .scan_record import ScanRecord  # noqa: F401
from .softgluezynq import SoftGlueZynq  # noqa: F401
from .tetramm import TetraMM  # noqa: F401
from .tetramm_test import Tetramm  # noqa: F401

# from .tetramm import tmm1  # noqa: F401
from .xspress3 import Xspress3  # noqa: F401

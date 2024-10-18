"""Ophyd-style devices."""

from ophyd.sim import motor as sim_motor  # noqa: F401
from ophyd.sim import noisy_det as sim_det  # noqa: F401

from ..utils.aps_functions import host_on_aps_subnet
from .positioner_stream import postrm
from .profile_move import pm1
from .save_data import savedata
from .softglue_zynq import sgz
from .tetramm import tmm1
from .xspress3 import xp3

# from .scan_record import scan1, scan2


if host_on_aps_subnet():
    """
    below add any devices that will only load succesfully on the aps network
    """

del host_on_aps_subnet

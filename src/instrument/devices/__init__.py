"""Ophyd-style devices."""

from ophyd.sim import motor as sim_motor  # noqa: F401
from ophyd.sim import noisy_det as sim_det  # noqa: F401

from ..utils.aps_functions import host_on_aps_subnet
from .positioner_stream import postrm  # noqa: F401
from .profile_move import pm1  # noqa: F401
from .save_data import savedata  # noqa: F401
from .softglue_zynq import sgz  # noqa: F401
from .tetramm import tmm1  # noqa: F401
from .xspress3 import xp3  # noqa: F401

# from .scan_record import scan1, scan2


if host_on_aps_subnet():
    """
    below add any devices that will only load succesfully on the aps network
    """

del host_on_aps_subnet

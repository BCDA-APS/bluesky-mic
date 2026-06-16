"""
A plan to enable or disable the usercalc that used in scan record at 2idd

@author: yluo(grace227)

"""

__all__ = """
    enable_usercalc
    disable_usercalc
""".split()

import logging

import bluesky.plan_stubs as bps
from apsbits.core.instrument_init import oregistry

logger = logging.getLogger(__name__)
logger.info(__file__)



def disable_usercalc():
    """
    Disable the selected usercalc found in the iconfig.yml
    """

    usercalcs = {
        "fly_calc10": oregistry["fly_calc10"],
        # "fly_calc2": oregistry["fly_calc2"],
        # "fly_calc3": oregistry["fly_calc3"],
        # "fly_calc4": oregistry["fly_calc4"],
    }

    for usercalc_name, usercalc_pv in usercalcs.items():
        # signal = EpicsSignal(usercalc_pv, name=usercalc_name)
        logger.info(f"Disabling {usercalc_name}: {usercalc_pv.pvname}")
        yield from bps.mv(usercalc_pv, 0)


def enable_usercalc():
    """
    Enable the selected usercalc found in the iconfig.yml
    """

    usercalcs = {
        "fly_calc10": oregistry["fly_calc10"],
        # "fly_calc2": oregistry["fly_calc2"],
        # "fly_calc3": oregistry["fly_calc3"],
        # "fly_calc4": oregistry["fly_calc4"],
    }

    for usercalc_name, usercalc_pv in usercalcs.items():
        # signal = EpicsSignal(usercalc_pv, name=usercalc_name)
        logger.info(f"Enabling {usercalc_name}: {usercalc_pv.pvname}")
        yield from bps.mv(usercalc_pv, 1)

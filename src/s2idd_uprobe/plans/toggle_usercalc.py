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
# from apsbits.utils.config_loaders import get_config
# from ophyd import EpicsSignal

logger = logging.getLogger(__name__)
logger.info(__file__)

# iconfig = get_config("iconfig.yml")

# usercalcs = iconfig.get("USERCALC_DISABLE", {})

usercalcs = {
    "usercalc_tmm1_filename": oregistry["usercalc_tmm1_filename"],
    "usercalc_tmm1_filetemplate": oregistry["usercalc_tmm1_filetemplate"],
    "usercalc_tmm2_filename": oregistry["usercalc_tmm2_filename"],
    "usercalc_tmm2_filetemplate": oregistry["usercalc_tmm2_filetemplate"],
    "usercalc_xmap_filename": oregistry["usercalc_xmap_filename"],
}


def disable_usercalc():
    """
    Disable the selected usercalc found in the iconfig.yml
    """
    for usercalc_name, usercalc_pv in usercalcs.items():
        # signal = EpicsSignal(usercalc_pv, name=usercalc_name)
        logger.info(f"Disabling {usercalc_name}: {usercalc_pv}")
        yield from bps.mv(usercalc_pv, 0)


def enable_usercalc():
    """
    Enable the selected usercalc found in the iconfig.yml
    """
    for usercalc_name, usercalc_pv in usercalcs.items():
        # signal = EpicsSignal(usercalc_pv, name=usercalc_name)
        logger.info(f"Enabling {usercalc_name}: {usercalc_pv}")
        yield from bps.mv(usercalc_pv, 1)

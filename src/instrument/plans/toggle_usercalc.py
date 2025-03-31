"""
A plan to enable or disable the usercalc that used in scan record at 2idd

@author: yluo(grace227)

"""

__all__ = """
    enable_usercalc
    disable_usercalc
""".split()

from mic_instrument.utils.config_loaders import iconfig
from ophyd import EpicsSignal
import bluesky.plan_stubs as bps

import logging
logger = logging.getLogger(__name__)
logger.info(__file__)


usercalcs = iconfig.get("USERCALC_DISABLE", {})


def disable_usercalc():
    '''
    Disable the selected usercalc found in the iconfig.yml
    '''
    for usercalc_name, usercalc_pv in usercalcs.items():
        signal = EpicsSignal(usercalc_pv, name = usercalc_name)
        logger.info(f"Disabling {usercalc_name}: {usercalc_pv}")
        yield from bps.mv(signal, 0)


def enable_usercalc():
    '''
    Enable the selected usercalc found in the iconfig.yml
    '''
    for usercalc_name, usercalc_pv in usercalcs.items():
        signal = EpicsSignal(usercalc_pv, name = usercalc_name)
        logger.info(f"Enabling {usercalc_name}: {usercalc_pv}")
        yield from bps.mv(signal, 1)





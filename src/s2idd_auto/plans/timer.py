import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import oregistry
import logging
import math

logger = logging.getLogger(__name__)

savedata = oregistry["savedata"]


def timer(sleep_time_minutes: float = 2, update_every_minutes: float = 0.1):
    """
    A timer plan that waits for a specified time.

    Parameters
    ----------
    sleep_time_minutes:
        The time to wait in minutes. Default is 1 minute. Type: float
    update_every_minutes:
        The time frequency to report the remaining time. Type: float
    """
    remaining = int(math.ceil(sleep_time_minutes * 60))
    logger.info("Starting timer")
    while remaining > 0:
        logger.info(f"Time remaining: {remaining/60} minutes")
        step = min(update_every_minutes * 60, remaining)
        yield from bps.sleep(step)
        yield from bps.checkpoint()
        remaining -= step
    logger.info("Timer finished")

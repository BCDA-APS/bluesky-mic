import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import oregistry
import logging

logger = logging.getLogger(__name__)

savedata = oregistry["savedata"]


def timer(sleep_time=1):
    """
    A timer plan that waits for a specified time.

    Parameters
    ----------
    sleep_time:
        The time to wait in seconds. Default is 1 second. Type: float
    """

    scan_id = None
    try:
        scan_id = savedata.next_scan_number.get()
    except Exception as e:
        logger.error(f"Error getting scan id: {e}")
        scan_id = None

    md = {"scan_id": scan_id}

    @bpp.run_decorator(md=md)
    def _timer():
        yield from _timer()

    logger.info(f"Waiting for {sleep_time} seconds")
    yield from bps.sleep(sleep_time)

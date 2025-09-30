import logging
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import oregistry
from apsbits.utils.config_loaders import get_config

iconfig = get_config()
logger = logging.getLogger(__name__)
logger.info(__file__)


savedata = oregistry["savedata"]

def test_logger():
    logger.info("test_logger")
    yield from bps.sleep(1)
    logger.info("test_logger 2")
    yield from bps.sleep(1)
    logger.info("test_logger 3")
    yield from bps.sleep(1)

    logger.info("end of test_logger")



        






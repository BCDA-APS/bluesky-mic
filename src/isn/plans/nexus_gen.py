from apsbits.core.instrument_init import oregistry
# from apsbits.utils.config_loaders import get_config
from bluesky.plan_stubs import mv, sleep
from isn.utils.param_capture import capture_params
import logging
import bluesky.preprocessors as bpp
from bluesky import plan_stubs as bps

logger = logging.getLogger(__name__)
logger.info(__file__)

sample = oregistry["sample"]


def nexus_gen(
    x_min=-50, # in um
    x_max=50, #in um
    x_npts=11,
    y_min=0, #in um
    y_max=90, #in um
    y_npts=11,
    acquire_time=80, # in ms
    det_dead=20, # in ms (detector dead time)
    F=0.9, # Fraction of wave in straight line 0-1
    interferometer_frequency = 1000 #in Hz
):

    """Capture the input plan parameters"""
    plan_args = capture_params(nexus_gen, **locals())
    x_center = sample.x.user_readback.get()
    y_center = sample.y.user_readback.get()
    md = {"plan_args": plan_args, "x_center_mm": x_center, "y_center_mm": y_center}

    @bpp.run_decorator(md=md)
    def _nexus_gen():
        # yield from flyscan(**plan_args)
        yield from bps.sleep(3)

    yield from _nexus_gen()


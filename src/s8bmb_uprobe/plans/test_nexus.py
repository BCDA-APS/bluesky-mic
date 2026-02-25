import logging
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from s2idd_uprobe.utils.param_capture import capture_params
from apsbits.core.instrument_init import oregistry
from apsbits.utils.config_loaders import get_config

iconfig = get_config()
logger = logging.getLogger(__name__)
logger.info(__file__)

samy = oregistry["samy"]
samx = oregistry["samx"]
savedata = oregistry["savedata"]


def test_nexus(dets, num=5, md={}):
    dict_params = capture_params(test_nexus, **locals())
    print(dict_params)

    def inner_test_nexus():
        for i in range(num):
            yield from bps.sleep(1)
            yield from bps.create("primary")
            for d in dets:
                yield from bps.read(d)
            yield from bps.save()

    @bpp.run_decorator(md=md)
    def outer_test_nexus():
        yield from bps.sleep(1)
        yield from bps.create("secondary")
        yield from bps.read(samx)
        yield from bps.save()
        yield from inner_test_nexus()

    yield from outer_test_nexus()

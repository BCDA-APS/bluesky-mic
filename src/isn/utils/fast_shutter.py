import bluesky.preprocessors as bpp
import bluesky.plan_stubs as bps

from apsbits.core.instrument_init import oregistry

fast_shutter = oregistry['fast_shutter']

def fast_shutter_control(plan):
    def open_plan():
        if fast_shutter._enabled:
            fast_shutter.open()
        yield from bps.null()
    def close_plan():
        if fast_shutter._enabled:
            fast_shutter.close()
        yield from bps.null()
    def combined_plan():
        yield from open_plan()
        yield from plan
    return bpp.finalize_wrapper(combined_plan(), close_plan())
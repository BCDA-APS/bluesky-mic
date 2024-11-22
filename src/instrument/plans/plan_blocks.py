from bluesky import preprocessors as bpp
import bluesky.plan_stubs as bps
from ophyd import Signal

flag = Signal(name="flag", value=True)

def watch_counter(value=None, **kwargs):
    flag.put(True)  # new value available

def take_reading(counter):
    yield from bps.create(name="primary")
    try:
        yield from bps.read(counter)
    except Exception as reason:
        print(reason)
    yield from bps.save()

@bpp.run_decorator(md={})
def count_subscriber(counter, scanrecord1):
    counter.subscribe(watch_counter) # Collect a new event each time the scaler updates
    while counter.value <= scanrecord1.number_points.value:
        if flag.get():
            yield from take_reading(counter)
            yield from bps.mv(flag, False)  # reset the flag
            if counter.value == scanrecord1.number_points.value:
                break
        yield from bps.sleep(0.1)

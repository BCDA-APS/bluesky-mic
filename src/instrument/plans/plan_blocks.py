from bluesky import preprocessors as bpp
import bluesky.plan_stubs as bps
from ophyd import Signal

# logger = logging.getLogger(__name__)

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
def count_subscriber(counter, setpoint):
    counter.subscribe(watch_counter)  # Collect a new event each time the scaler updates
    while counter.value <= setpoint:
        # print("In counter_subscriber")
        if flag.get():
            # logger.info(f"{old_value=}, {value=}")
            # print(f"{counter=}")
            yield from take_reading(counter)
            yield from bps.mv(flag, False)  # reset the flag
            if counter.value == setpoint:
                break
        # else:
        #     print("Not getting flag")

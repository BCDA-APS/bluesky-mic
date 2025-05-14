"simple count down plan to test interrupts"

__all__ = """
    test_plan
""".split()

import logging

import bluesky.plan_stubs as bps
from ophyd import EpicsMotor

logger = logging.getLogger(__name__)
logger.info(__file__)


def test_plan(timer=10):
    m1 = EpicsMotor("hometst:m1", name="m1")
    while timer > 0:
        pos = m1.report["position"]
        print(timer, f"motor position: {pos}")
        yield from bps.sleep(1)
        while pos == 2:
            print(f"motor position at 2, pausing plan.. : {timer}, {pos}")
            pos = m1.report["position"]
            yield from bps.sleep(1)
        timer -= 1

    print("end of plan\n")

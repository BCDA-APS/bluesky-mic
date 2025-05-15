"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    dummy_testing
""".split()

import logging

import bluesky.plan_stubs as bps

logger = logging.getLogger(__name__)
logger.info(__file__)


def dummy_testing(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
    dwell=0,
    smp_theta=None,
    simdet_on=False,
    xrf_on=True,
    ptycho_on=False,
    preamp_on=False,
    fpga_on=False,
    position_stream=False,
    wf_run=False,
    analysisMachine="mona2",
    eta=0,
):
    """Bluesky plan for testing but not moving any actual hardware"""

    for i in range(stepsize_x):
        prog = round(i / stepsize_x * 100, 2)
        msg = "{"
        msg += f"Filename: 2xfm_0001.mda, Scan_progress: {prog}%, "
        msg += f"Line: 1/1, Scan_remaining: {(stepsize_x-i)*dwell}, "
        msg += f"Scanned {i}/{stepsize_x}"
        msg += "}"
        logger.info(msg)
        # logger.info(f"Scan progress: dummy_test: {prog}% :, scanned {i}/{stepsize_x}")
        yield from bps.sleep(dwell)

    logger.info("end of plan")

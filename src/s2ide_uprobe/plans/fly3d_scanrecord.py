"""
A bluesky plan that can perform lamnilogaphy scans.

@author: yluo(grace227)


"""

__all__ = """
    fly3d_scanrecord
""".split()

import logging
from .fly2d_scanrecord import fly2d_scanrecord
import numpy as np
import bluesky.plan_stubs as bps

logger = logging.getLogger(__name__)
logger.info(__file__)


def fly3d_scanrecord(
    samplename="smp1",
    user_comments="",
    smp_theta_start=None,
    smp_theta_end=None,
    smp_theta_stepsize=None,
    width=0,
    x_center=None,
    stepsize_x=0,
    height=0,
    y_center=None,
    stepsize_y=0,
    dwell=0,
    smp_theta=None,
    xrf_on=True,
    ptycho_on=True,
    eta=0,
    ptycho_exp_factor=3,
):
    """Create and move sample theta before 2D scan"""

    sample_angles = np.arange(smp_theta_start, smp_theta_end + smp_theta_stepsize, smp_theta_stepsize)
    logger.info(f"The requested sample angles are {sample_angles}")

    for i, smp_theta in enumerate(sample_angles):
        logger.info(
            f"Preparing stage to run lamni_2d scan at {smp_theta} degrees, {i+1} of {len(sample_angles)} angles"
        )
        yield from fly2d_scanrecord(
            samplename=samplename,
            user_comments=user_comments,
            smp_theta=smp_theta,
            width=width,
            x_center=x_center,
            stepsize_x=stepsize_x,
            height=height,
            y_center=y_center,
            stepsize_y=stepsize_y,
            dwell=dwell,
            xrf_on=xrf_on,
            ptycho_on=ptycho_on,
            ptycho_exp_factor=ptycho_exp_factor,
        )
        yield from bps.sleep(1)

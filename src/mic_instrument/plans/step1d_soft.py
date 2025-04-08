"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    step1d
""".split()

import logging

logger = logging.getLogger(__name__)
logger.info(__file__)


def step1d_soft(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
    dwell=0,
    smp_theta=None,
    simdet_on=False,
    xrf_me7_on=True,
    ptycho_on=False,
    preamp_on=False,
    fpga_on=False,
    position_stream=False,
    wf_run=False,
    analysisMachine="mona2",
):
    """Execute a 1D step scan with soft X-rays.

    Parameters
    ----------
    samplename : str, optional
        Name of the sample, by default "smp1"
    user_comments : str, optional
        User comments about the scan, by default ""
    width : float, optional
        Total width of the scan, by default 0
    x_center : float, optional
        Center position of the scan, by default None
    stepsize_x : float, optional
        Step size for the scan, by default 0
    dwell : float, optional
        Dwell time per step, by default 0
    smp_theta : float, optional
        Sample theta angle, by default None
    simdet_on : bool, optional
        Whether to use simulated detector, by default False
    xrf_me7_on : bool, optional
        Whether to use XRF ME7, by default True
    ptycho_on : bool, optional
        Whether to use ptychography, by default False
    preamp_on : bool, optional
        Whether to use preamp, by default False
    fpga_on : bool, optional
        Whether to use FPGA, by default False
    position_stream : bool, optional
        Whether to stream position data, by default False
    wf_run : bool, optional
        Whether this is a workflow run, by default False
    analysisMachine : str, optional
        Analysis machine to use, by default "mona2"

    Returns
    -------
    None
    """
    # Implementation will be added here
    pass

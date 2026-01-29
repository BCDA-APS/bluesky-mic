"""
Fly1D plan for 2idd. A building block for fly2d_noScanRecord plan.

This module provides a 1D flyscan plan that performs continuous motion scanning along the x-axis
without relying on Scan Record.

Plan Description:
----------------
Execute a 1D flyscan where the x-motor moves at a calculated speed while detectors continuously 
capture data. The scan follows this sequence:

1. Setup and validation of scan parameters and detector connections
2. Configure detector settings and file I/O based on scan parameters
3. Position the x-motor at the start position and set scan speed
4. Execute the scan by moving the x-motor to the end position
5. Wait for all detector data to be captured and saved
6. Retrace the x-motor to the start position at high speed
7. Restore motor speed to scan speed for potential subsequent scans

Key Features:
-------------
- Automatic motor speed calculation based on step size and dwell time
- Detector synchronization for data integrity
- Configurable detector selection (XRF, preamp1, preamp2)
- Automatic file I/O configuration
- Motor speed optimization for scan and retrace operations

@author: yluo(grace227)
"""


import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import oregistry
from s2idd_uprobe.plans.flyscan_core import _fly1d
from mic_common.utils.param_capture import capture_params
from mic_common.utils.validation import validate_scan_parameters
import logging

logger = logging.getLogger(__name__)

savedata = oregistry["savedata"]
sample = oregistry["sample"]

def fly1d(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
    dwell_ms=0,
    sample_z=None,
    xrf_on=True,
    preamp1_on=False,
):
    """
    Execute a 1D flyscan along the x-axis.

    See module header for detailed description of the scan process and features.

    Parameters
    ----------
    samplename : str, optional
        The name of the sample for file naming. Default is "smp1".
    user_comments : str, optional
        User comments to be recorded with the scan data. Default is "".
    width : float
        The total width of the scan in motor units.
    x_center : float, optional
        The center position of the scan in the x-direction. If not provided,
        the current x-motor position will be used as the center.
    stepsize_x : float
        The step size (spatial resolution) of the scan in motor units.
    dwell : float
        The dwell time per step in milliseconds.
    sample_z : float, optional
        The sample z position. If not provided, the current sample z position
        will be maintained.
    xrf_on : bool, optional
        Whether to enable the x-ray fluorescence detector. Default is True.
    preamp1_on : bool, optional
        Whether to enable preamp1. Default is False.
    """

    validate_scan_parameters(width=width, stepsize_x=stepsize_x, dwell_ms=dwell_ms)
    x_center = x_center if x_center is not None else (round(sample.x.position - width / 2, 2))
    sample_z = sample_z if sample_z is not None else (round(sample.z.position, 2))

    plan_args = capture_params(fly1d, **locals())
    logger.info(f"Plan arguments: {plan_args}")

    scan_id = None
    try:
        scan_id = savedata.next_scan_number.get()
        logger.info(f"Scan id: {scan_id}")
    except Exception as e:
        logger.error(f"Error getting scan id: {e}")
        scan_id = None

    md = {"plan_args": plan_args, "scan_id": scan_id}

    @bpp.run_decorator(md=md)
    def _fly1d_wrapper():
        yield from _fly1d(**plan_args)

    yield from _fly1d_wrapper()

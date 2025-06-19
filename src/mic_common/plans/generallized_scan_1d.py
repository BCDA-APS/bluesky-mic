"""
Creating a general scan 1D function that can be modify to perform either
fly / step scans and also drive different positioners

@author: yluo(grace227)

"""

__all__ = """
    generalized_scan_1d
""".split()

import logging
from mic_common.utils.scan_monitor import execute_scan_1d


logger = logging.getLogger(__name__)
logger.info(__file__)


def generalized_scan_1d(
    scanrecord,
    positioner,
    savedata,
    scan_overhead=0,
    scanmode="LINEAR",
    x_center=None,
    width=0,
    stepsize_x=0,
    dwell=0,
    exec_plan=False,
):
    """
    Generalized scan 1D function that can be modify to perform either
    fly / step scans and also drive different positioners
    """

    logger.info(f"Using {scanrecord.prefix} as the scanRecord")
    logger.info(f"Using {positioner} as the motor")
    if scanrecord.connected and positioner.connected:
        logger.info(f"{scanrecord.prefix} is connected")
        logger.info(f"{positioner} is connected")

        """Set up scan mode to be either FLY or STEP """
        yield from scanrecord.set_scan_mode(scanmode)

        """Assign the desired positioner in scanrecord """
        try:
            yield from scanrecord.set_positioner_drive(f"{positioner.prefix}.VAL")
            yield from scanrecord.set_positioner_readback(f"{positioner.prefix}.RBV")
        except Exception as e:
            msg = f"Fail to set positioner in {scanrecord.prefix} due to {e}"
            logger.info(msg)
            yield from scanrecord.set_positioner_drive(f"{positioner.pvname}")
            yield from scanrecord.set_positioner_readback(f"{positioner.pvname}")

        """Set up scan parameters and get estimated time of a scan"""
        yield from scanrecord.set_center_width_stepsize(x_center, width, stepsize_x)
        numpts_x = scanrecord.number_points.value
        eta = numpts_x * dwell * (1 + scan_overhead)
        logger.info(f"Number_points in X: {numpts_x}")
        logger.info(f"Estimated_time for this scan is {eta}")

        """Start executing scan"""
        if exec_plan:
            savedata.update_next_file_name()
            yield from execute_scan_1d(scanrecord, scan_name=savedata.next_file_name)

"""
A bluesky plan that performs 1D XANES scan.

@author: yluo(grace227)


"""

__all__ = """
    xane_spec
""".split()

import bluesky.plan_stubs as bps
from mic_instrument.configs.device_config import samx
from mic_instrument.configs.device_config import samy
from mic_instrument.configs.device_config import savedata
from mic_instrument.configs.device_config import scan1
from mic_instrument.configs.device_config import xrf
from mic_instrument.utils.scan_monitor import execute_scan_1d


def xane_spec(
    samplename="smp1",
    user_comments="",
    x_center=None,
    y_center=None,
    eng_center=None,
    eng_width=None,
    eng_stepsize=0.0005,
    dwell_sec=0,
):
    """
    Perform a 1D XANES scan.

    Parameters
    ----------
    samplename :
        Str: The name of the sample.
    user_comments :
        Str: The user comments for the scan.
    x_center :
        Float: The center of the sample-X position.
    y_center :
        Float: The center of the sample-Y position.
    eng_center :
        Float: The center of the monochromator energy.
    eng_width :
        Float: The width of the energy that the monochromator will scan.
    eng_inc :
        Float: The increment of the energy that the monochromator will scan.
    dwell_sec :
        Float: The dwell time of the scan in seconds.
    """

    """Move to the desired sample position"""
    yield from bps.mv(samx, x_center)
    yield from bps.mv(samy, y_center)

    """Set up the scan record"""
    yield from scan1.set_center_width_stepsize(eng_center, eng_width, eng_stepsize)

    """Update the detector dwell time"""
    yield from xrf.set_real_time(dwell_sec)

    """Start executing scan"""
    savedata.update_next_file_name()
    yield from execute_scan_1d(scan1, scan_name=savedata.next_file_name)

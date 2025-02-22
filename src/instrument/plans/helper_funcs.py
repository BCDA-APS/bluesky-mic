"""
Helper functions that would be used in the plans

@author: yluo(grace227)

"""

__all__ = """
    selected_dets
""".split()

from mic_instrument.configs.device_config import det_name_mapping


def selected_dets(kwargs):
    """
    Select the detectors that are on based on the user input
    """
    dets = {}
    rm_str = "_on"
    for k, v in kwargs.items():
        if all([v, isinstance(v, bool), rm_str in k]):
            det_str = k[: -len(rm_str)]
            dets.update({det_str: det_name_mapping[det_str]})
    return dets


def calculate_num_capture(num_pts):
    """
    Calculate the number of capture for the XRF detector
    """
    return 1 if (num_pts <= xmap_buffer) else 2

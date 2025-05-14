"""
A collection of scan logic for before and after flyscan at 2IDE

The code mostly handles XMAP, SIS3820, Eiger and the file plugins for each detector

@author: yluo(grace227)

"""

__all__ = """
    before_flyscan
    after_flyscan
""".split()

import logging

# import os
# from ..utils.scan_monitor import execute_scan_1d
# from .dm_plans import dm_submit_workflow_job
from ..configs.device_config import (
    # savedata,
    sis3820,
    # hydra1_startposition,
    # stepdwell,
    xrf_dm_args,
    ptychoxrf_dm_args,
    ptychodus_dm_args,
)

# from .workflow_plan import run_workflow
# from ..utils.dm_utils import dm_upload_wait
# from ..devices.data_management import api
# from apstools.devices import DM_WorkflowConnector
# import bluesky.plan_stubs as bps
# from mic_instrument.configs.device_config import xmap_buffer


logger = logging.getLogger(__name__)
logger.info(__file__)

# SCAN_OVERHEAD = 0.3
# XMAP_BUFFER = 124


def setup_flyscan_XRF_triggers(scanrecord, xrf, xrf_netcdf, sis3820, num_pulses):
    """
    Set up the triggers for the fly scan.

    Config the SIS3820 struck card to send out pulses, then
    set the triggers for the inner fly scanrecord and tweak the hydra1 start position

    Three triggers are needed for the inner fly scanrecord:
    Trigger 1: Toggle XMAP netcdf file writer capture state
    Trigger 2: Toggle XMAP erase and start state
    Trigger 3: Toggle SIS3820 (struck card) erase and start state
    """

    yield from sis3820.before_flyscan(num_pulses)

    trigger_pvs = [
        xrf_netcdf.capture.pvname.replace("_RBV", ""),
        xrf.erase_start.pvname,
        sis3820.erase_start.pvname,
    ]
    yield from scanrecord.set_detTriggers(trigger_pvs)


def setup_flyscan_ptycho_triggers(
    outter_scanrecord, inner_scanrecord, eiger, eiger_filewriter=None
):
    """
    Set up the detector triggers for eiger detector.

    For 2-ID, the eiger and filewriter arming will be done in the outter loop.

    Commonly, three triggers are needed for the outter loop:
    Trigger 1: Toggle inner scanrecord execute state
    Trigger 2: Toggle filewriter capture state
    Trigger 3: Toggle eiger acquire state
    """

    filewriter_capture_pv = ""
    if eiger_filewriter is not None:
        filewriter_capture_pv = eiger_filewriter.capture.pvname.replace("_RBV", "")

    trigger_pvs = [
        inner_scanrecord.execute_scans.pvname,
        filewriter_capture_pv,
        eiger.acquire.pvname.replace("_RBV", ""),
    ]
    yield from outter_scanrecord.set_trigger_pv(trigger_pvs)


def setup_eiger_filewriter(
    eiger,
    eiger_filewriter,
    savedata,
    det_name,
    num_pulses,
    filename,
    beamline_delimiter,
):
    """
    Set up the eiger filewriter.

    Preparing for Eiger/Ptycho data collection
    if eiger_filewriter is None, use the default filewriter from Eiger
    Else, use the filewriter from ad_fileplugin
    """

    # Set up the filewriter to save the eiger data
    if eiger_filewriter is None:
        try:
            yield from eiger.setup_eiger_filewriter(
                savedata, det_name, filename, beamline_delimiter
            )
            eiger_filewriter = eiger
        except Exception as e:
            logger.error(
                f"Error occurs when setting up eiger filewriter: {eiger_filewriter}: {e}"
            )
    else:
        try:
            yield from eiger_filewriter.setup_file_writer(
                savedata,
                det_name,
                num_pulses,
                filename_pattern=filename,
                beamline_delimiter=beamline_delimiter,
            )
        except Exception as e:
            logger.error(f"Error occurs when setting up {eiger_filewriter.prefix}: {e}")

    if not eiger_filewriter.file_path_exists.get():
        raise ValueError(f"File path {eiger_filewriter.file_path.get()} does not exist")


# def before_flyscan(start_position, stepsize, num_pts, dets,
#                    dwell, ptycho_exp_factor=1, savedata=None,
#                    filename="test_", beamline_delimiter=""):

#     # # """Preparing for SIS3820 data collection"""
#     # # if sis3820.connected:
#     # #     yield from sis3820.set_stop_all(1)
#     # #     yield from sis3820.set_num_ch_used(num_pts - 2)

#     # """Preparing for XRF data collection"""
#     # if "xrf" in dets.keys():
#     #     xrf = dets["xrf"]["cam"]
#     #     xrf_netcdf = dets["xrf"]["file_plugin"]
#     #     num_capture = 1 if (num_pts <= XMAP_BUFFER) else 2

#     #     # yield from xrf_netcdf.set_capture("done")
#     #     # yield from xrf_netcdf.set_num_capture(num_capture)
#     #     # yield from xrf_netcdf.set_filename(savedata.get().full_name.replace(".mda", "_"))
#     #     # yield from xrf_netcdf.set_filenumber(0)
#     #     # yield from xrf.set_collection_mode("MCA MAPPING")

#     #     # yield from xrf.set_stop_all(1)
#     #     # yield from xrf.set_pixels_per_run(num_pts - 2)
#     #     # yield from bps.mv(hydra1_startposition, start_position+stepsize)
#     #     yield from xrf_netcdf.set_capture("capturing")


#     if "ptycho" in dets.keys():
#         eiger = dets["ptycho"]["cam"]
#         print(type(eiger))
#         eiger_filewriter = dets["ptycho"]["file_plugin"]
#         det_name = "ptycho"
#         ready = False

#         # Set up the eiger detector based on the trigger mode
#         if eiger is not None:
#             trigger_mode = eiger.trigger_mode.get(as_string=True)
#             if trigger_mode == "External Series":
#                 yield from eiger.setup_external_series_trigger(num_pts, dwell, ptycho_exp_factor)
#             elif trigger_mode == "External Enable":
#                 yield from eiger.setup_external_enable_trigger(num_pts, dwell, ptycho_exp_factor)


# def after_flyscan(kwargs):
#     pass

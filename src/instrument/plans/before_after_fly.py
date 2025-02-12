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
import os
from ..utils.scan_monitor import execute_scan_1d
from .dm_plans import dm_submit_workflow_job
from ..configs.device_config import (
    savedata,
    sis3820,
    hydra1_startposition,
    stepdwell,
    xrf_dm_args,
    ptychoxrf_dm_args,
    ptychodus_dm_args,
)
from .workflow_plan import run_workflow
from ..utils.dm_utils import dm_upload_wait
from ..devices.data_management import api
from apstools.devices import DM_WorkflowConnector
import bluesky.plan_stubs as bps



logger = logging.getLogger(__name__)
logger.info(__file__)

SCAN_OVERHEAD = 0.3
XMAP_BUFFER = 124



def before_flyscan(start_position, stepsize, num_pts, dets, 
                   ptycho_exp_factor=1):

    """Preparing for XRF data collection"""
    if "xrf" in dets.keys():
        xrf = dets["xrf"]["cam"]
        xrf_netcdf = dets["xrf"]["file_plugin"]
        num_capture = 1 if (num_pts <= XMAP_BUFFER) else 2

        yield from xrf_netcdf.set_capture(0)
        yield from xrf_netcdf.set_num_capture(num_capture)
        yield from xrf_netcdf.set_filename(savedata.get().full_name.replace(".mda", "_"))
        yield from xrf_netcdf.set_filenumber(0)
        yield from xrf.set_collection_mode("MCA MAPPING")

        if sis3820.connected:
            yield from sis3820.set_stop_all(1)
            yield from sis3820.set_num_ch_used(num_pts - 2)

        yield from xrf.set_stop_all(1)
        yield from xrf.set_pixels_per_run(num_pts - 2)
        yield from bps.mv(hydra1_startposition, start_position+stepsize)
        yield from xrf_netcdf.set_capture(1)

    """Preparing for Eiger/Ptycho data collection"""
    if "ptycho" in dets.keys():
        eiger = dets["ptycho"]["cam"]
        # yield from eiger.set_trigger_mode("External Enable")


        # yield from eiger_netcdf.set_capture(0)
        # yield from eiger_netcdf.set_num_capture(num_capture)
        # yield from eiger_netcdf.set_filename(savedata.get().full_name.replace(".mda", "_"))
        # yield from eiger_netcdf.set_filenumber(0)
    
    

def after_flyscan(kwargs):
    pass

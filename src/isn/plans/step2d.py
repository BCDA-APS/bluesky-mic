"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    step2d
""".split()

import logging

from apsbits.utils.controls_setup import oregistry
from bluesky import plan_stubs as bps
from mic_common.utils.scan_monitor import execute_scan_2d

from .generallized_scan_1d import generalized_scan_1d
from bluesky import plan_stubs as bps  
from apsbits.utils.config_loaders import get_config, load_config_yaml
from mic_common.utils.watch_pvs_write_hdf5 import write_scan_master_h5
from pathlib import Path
from isn.plans.utils.det_setup import xrf_me7_setup, ptycho_setup
from isn.startup import master_file_config_path
import h5py, os

logger = logging.getLogger(__name__)
logger.info(__file__)


scan1 = oregistry["scan1"]
scan2 = oregistry["scan2"]
samx = oregistry["samx"]
samy = oregistry["samy"]
savedata = oregistry["savedata"]
shutter_open = oregistry["shutter_open"]
shutter_close = oregistry["shutter_close"]
shutter_open_status = oregistry["shutter_open_status"]
ptycho = oregistry["ptycho"]
ptycho_hdf = oregistry["ptycho_hdf"]
xrf_me7 = oregistry["xrf_me7"]
xrf_me7_hdf = oregistry["xrf_me7_hdf"]

iconfig = get_config()
netcdf_delimiter = iconfig.get("FILE_DELIMITER")
xrf_me7_folder = iconfig.get("XRF_ME7_FOLDER")
ptycho_folder = iconfig.get("PTYCHO_FOLDER")

master_file_yaml = load_config_yaml(master_file_config_path)

scanmode = "LINEAR"


def step2d(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
    height=0,
    y_center=None,
    stepsize_y=0,
    dwell=0,
    xrf_me7_on=True,
    ptycho_on=False,
    ptycho_exp_factor=1,
):
    """2D Bluesky plan that drives the x- and y- sample motors in stepping mode using
    ScanRecord

    The plan will drive samx and samy to the requested x_center and y_center,
    and then perform a relative scan in the x and y directions.

    Parameters
    ----------
    samplename:
        Str: The name of the sample
    user_comments:
        Str: The user comments for the scan
    width:
        Float: The width of the scan
    x_center:
        Float: The center of the scan in the x direction. Default is None which uses the current position of samx
    stepsize_x:
        Float: The step size in the x direction
    height:
        Float: The height of the scan
    y_center:
        Float: The center of the scan in the y direction. Default is None which uses the current position of samy
    stepsize_y:
        Float: The step size in the y direction
    dwell:
        Float: The dwell time in the scan
    xrf_me7_on:
        Bool: Whether to collect XRF data
    ptycho_on:
        Bool: Whether to collect Ptycho data
    ptycho_exp_factor:
        Float: The exposure factor for the ptycho camera
    """

    def get_bluesky_params():
        """Create a dictionary of function name and input parameters."""
        import inspect

        # Get the name of the outer function
        outer_frame = inspect.currentframe().f_back
        func_name = outer_frame.f_code.co_name

        # Get all local variables from the outer function
        outer_locals = outer_frame.f_locals

        # Filter out special variables and functions
        params = {"plan_name": func_name.replace("_masterfile", "")}
        for k, v in outer_locals.items():
            if not k.startswith('__') and not callable(v):
                params.update({k:v})

        return params
    
    """Put the plan parameters in to dict"""
    bluesky_params = get_bluesky_params()

    """Open the shutter"""
    logger.info("Opening the shutter")
    yield from bps.mv(shutter_open, 1)
    shutter_status = shutter_open_status.value  # when open, the status becomes 0
    while shutter_status:
        shutter_status = shutter_open_status.value
        yield from bps.sleep(0.2)

    """Move to the requested x- and y- centers"""
    logger.info("Moving to the requested x- and y- centers")
    if x_center is not None:
        yield from bps.mv(samx, x_center)
    if y_center is not None:
        yield from bps.mv(samy, y_center)

    """Set up the inner loop scan record based on the scan types and parameters"""
    yield from bps.mv(scan1.positioners.p1.abs_rel, "relative".upper())
    yield from generalized_scan_1d(scan1, samy, scanmode=scanmode, x_center=0, width=height, 
                                stepsize_x=stepsize_y, dwell=dwell)

    """Set up the outter loop scan record"""
    yield from scan2.set_scan_mode(scanmode)
    yield from bps.mv(scan2.positioners.p1.abs_rel, "relative".upper())
    yield from generalized_scan_1d(scan2, samx, scanmode=scanmode, x_center=0, width=width, 
                            stepsize_x=stepsize_x, dwell=dwell)

    
    """Configure the detectors"""
    num_capture = scan1.number_points.get()
    savedata.update_next_file_name()
    filename = savedata.next_file_name.replace(".mda", "")
    
    if ptycho_on and ptycho.connected and ptycho_hdf.connected:
        trigger_mode = "Internal Series"
        yield from ptycho_setup(trigger_mode, num_capture, dwell, 
                                ptycho_exp_factor, filename)
        
    """Generate the scan master file"""
    next_file_name = savedata.next_file_name.replace(".mda", "_master.h5")
    scan_master_h5_path = Path(savedata.file_system.value) / next_file_name
    write_scan_master_h5(master_file_yaml, scan_master_h5_path, bluesky_params)
    logger.info(f"Scan master file saved to {scan_master_h5_path}")
        
    
    """Start executing scan"""
    savedata.update_next_file_name()
    yield from execute_scan_2d(scan1, scan2, scan_name=savedata.next_file_name)

    """Close the shutter"""
    yield from bps.mv(shutter_close, 1)
    shutter_status = shutter_open_status.value  # when open, the status becomes 0
    while not shutter_status:
        shutter_status = shutter_open_status.value
        yield from bps.sleep(0.2)


    """Disable manual trigger of eiger"""
    if ptycho_on and ptycho.connected:
        yield from ptycho.set_manual_trigger("Disable")
    
    """Generate detector master file and update detector h5 master file in the scan master file"""
    det_h5_master_path = {}
    dets = {}
    logger.info(f"Generating detector master file and updating detector h5 master file in the scan master file")
    if ptycho_on and ptycho.connected and ptycho_hdf.connected:
        dets.update({'ptycho':{'cam':ptycho, 'file_plugin':ptycho_hdf}})
    if xrf_me7_on and xrf_me7.connected and xrf_me7_hdf.connected:
        dets.update({'xrf_me7':{'cam':xrf_me7, 'file_plugin':xrf_me7_hdf}})
    
    for det_name, det_var in dets.items():
        cam = det_var['cam']
        file_plugin = det_var['file_plugin']
        cap_det_name = det_name.upper()
        det_dir = file_plugin.file_path.value
        master_h5_path = Path(det_dir) / next_file_name.replace("_master.h5", ".h5")
        try:
            cam.write_h5(master_h5_path, det_dir, filename, cap_det_name)
            det_h5_master_path[cap_det_name] = master_h5_path
        except Exception as e:
            logger.error(f"Error writing HDF5 file for {cap_det_name}: {e}")

    with h5py.File(scan_master_h5_path, 'r+') as f:
        group = f.create_group("DETECTORS")
        for det_name, master_h5_path in det_h5_master_path.items():
            rel_path = os.path.relpath(Path(master_h5_path), Path(scan_master_h5_path).parent)
            group[det_name] = h5py.ExternalLink(rel_path, det_name)

    yield from bps.sleep(0.2)
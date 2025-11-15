from isn.configs.dm_workflow_configs import master_file_yaml
from mic_common.utils.watch_pvs_write_hdf5 import write_scan_master_h5
from apsbits.core.instrument_init import oregistry
from pathlib import Path
import h5py
import os
import logging

logger = logging.getLogger(__name__)
logger.info(__file__)
savedata = oregistry["savedata"]

def generate_scan_master_h5(scan_num: int = None, bluesky_params: dict = None, dets: list = None):
    """Generate the scan master HDF5 file for the scan"""
    
    if scan_num is None:
        scan_num = savedata.next_scan_number.get()

    try:
        scan_master_h5_path = write_master_h5(scan_num=scan_num, bluesky_params=bluesky_params)
        det_h5_master_path = write_det_master_h5(scan_num=scan_num, dets=dets)
        append_det_master_h5_to_scan_master_h5(scan_master_h5_path=scan_master_h5_path, det_h5_master_path=det_h5_master_path)
    except Exception as e:
        logger.error(f"Error generating scan master HDF5 file: {e}")
        


def write_master_h5(scan_num: int = None, bluesky_params: dict = None):
    """Write the master HDF5 file for the scan"""
    
    try:
        savedata = oregistry["savedata"]
        file_path = savedata.file_system.get()
    except KeyError:
        raise ValueError("Savedata is not initialized")

    scan_master_h5_path = Path(file_path) / f"scan_{scan_num:04d}_master.h5"
    write_scan_master_h5(master_file_yaml, scan_master_h5_path, bluesky_params)
    logger.info(f"Scan master file saved to {scan_master_h5_path}")
    return scan_master_h5_path


def write_det_master_h5(scan_num: int = None, dets: list = None):
    """Write the detector master HDF5 file for the scan"""

    det_h5_master_path = {}

    if dets is not None:
        for det in dets:
            det_name = det.name.upper()
            det_path = det.hdf1.file_path.get()
            scan_num = scan_num
            det_h5 = Path(det_path) / f"scan_{scan_num:04d}.h5"
            print("writing master h5 file for detector: ", det_name)
            print(f"det_h5: {det_h5}")
            print(f"det_path: {det_path}")
            print(f"scan_name: scan_{scan_num:04d}.h5")
            print(f"det_name: {det_name}")
            det.write_master_h5(
                masterfile_path=det_h5, 
                detector_path=det_path, 
                scan_name=f"scan_{scan_num:04d}", 
                det_name=det_name)
            det_h5_master_path[det_name] = det_h5

    return det_h5_master_path


def append_det_master_h5_to_scan_master_h5(scan_master_h5_path: Path = None, det_h5_master_path: dict = None):
    """Append the detector master HDF5 file to the scan master HDF5 file"""
    
    with h5py.File(scan_master_h5_path, "r+") as f:
        group = f.create_group("detectors")
        for det_name, master_h5_path in det_h5_master_path.items():
            rel_path = os.path.relpath(
                Path(master_h5_path), Path(scan_master_h5_path).parent
            )
            group[det_name] = h5py.ExternalLink(rel_path, det_name)

    logger.info(
        "Detector master file and detector h5 master file in the scan master file "
        "have been updated"
    )


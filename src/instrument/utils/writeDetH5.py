import os
import datetime
import h5py
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
logger.info(__file__)

def write_det_h5(
    masterfile_path: str = '',
    det_dir: str = '',
    scan_name: str = '',
    det_name: str = '',
    det_file_ext: str = ".h5",
    det_key: str = "/entry",
    det_attrs_values: dict = {}
):
    
    with h5py.File(masterfile_path, "w") as f:

        configs = f.create_group("configs")
        for desc, value in det_attrs_values.items():
            ds = configs.create_dataset(desc, data=str(value))

        group = f.create_group(det_name)
        files = [fn for fn in os.listdir(det_dir) if scan_name in fn]
        if det_file_ext != ".nc":
            try:    
                for i, fn in enumerate(files):
                    if fn != os.path.basename(masterfile_path):
                        # Use os.path.relpath to get relative path from masterfile to detector file
                        rel_path = os.path.relpath(Path(det_dir) / fn, Path(masterfile_path).parent)
                        group[f"{fn}"] = h5py.ExternalLink(rel_path, det_key)
            except Exception as e:
                logger.error(f"Error in write_det_h5() creating external link for {fn}: {e}")
        else:
            group[f"{fn}"] = Path(det_dir) / fn

    logger.info(f"Master file ({masterfile_path}) has been created successfully")


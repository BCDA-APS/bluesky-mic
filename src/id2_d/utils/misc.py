"""
Miscellaneous utility functions for Bluesky workflows, including file and PV helpers.
"""

__all__ = [
    "mkdir",
    "mksubdirs",
    "pvget",
    "pvput",
    "pause_scan",
    "resume_scan",
    "abort_scan",
    "run_subprocess",
    "scan_number_in_list",
    "create_master_file",
]
import os
import subprocess

import h5py


def mkdir(directory):
    """Create a directory if it does not exist."""
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
            print(f"Created directory: {directory}")
        except OSError as e:
            print(f"Failed to create directory: {directory} - {e}")
    else:
        print(f"Directory already exists: {directory}")


def mksubdirs(save_path, subdirs=[]):
    """Create multiple subdirectories under a given path."""
    for folder in subdirs:
        path = f"{save_path}{folder}"
        mkdir(path)


def pvget(pv):
    """Get the value of a process variable (PV) using pvget command."""
    try:
        cmd = f"pvget {pv}"
        result = subprocess.getstatusoutput(cmd)
    except subprocess.CalledProcessError as e:
        result = e


def pvput(pv, value):
    """Set the value of a process variable (PV) using pvput command."""
    try:
        cmd = f"pvput {pv} {value}"
        result = subprocess.getstatusoutput(cmd)
    except subprocess.CalledProcessError as e:
        result = e


def run_subprocess(command_list):
    """Run a subprocess command and return the result."""
    try:
        result = subprocess.getstatusoutput(command_list)
    except subprocess.CalledProcessError as e:
        result = e
        pass
    return result


def pause_scan():
    """Pause the current scan by setting the scan2.wcnt PV appropriately."""
    from ..devices.scan_record import scan2

    wcnt = scan2.wcnt.get()
    if wcnt == 0:
        scan2.wcnt.put(1)
    elif wcnt > 1:
        for i in range(wcnt - 1):
            scan2.wcnt.put(0)
    print("pausing scan")


def resume_scan():
    """Resume the current scan by resetting the scan2.wcnt PV."""
    from ..devices.scan_record import scan2

    wcnt = scan2.wcnt.get()
    if wcnt >= 1:
        for i in range(wcnt):
            scan2.wcnt.put(0)
    print("resuming scan...")


def abort_scan():
    """Abort the current scan by pausing and setting the AbortScan2 PV."""
    pause_scan()
    from ..devices.scan_record import scan2

    scan2.AbortScan2.put(1)
    scan2.AbortScan2.put(1)
    scan2.AbortScan2.put(1)
    print("aborting scan...")


def scan_number_in_list(lst, partial_str):
    """Find the first file in a list that matches a partial scan number string."""
    matches = [s for s in lst if partial_str in s]
    if len(matches) > 1:
        print("warning, more than one file matching scan number somehow")
    elif len(matches) == 0:
        print(
            "warning, no matches found, check that files are being saved and closing correctly"
        )
    elif len(matches) == 1:
        pass
    else:
        print("not sure how we got here, something very wrong")
    return matches[0]


def create_master_file(
    basedir,
    sample_name,
    scan_number,
    groups=None,
):
    """Create a master HDF5 file linking scan data files for a given scan number."""
    if groups is None:
        groups = ["flyXRF", "eiger", "mda", "tetramm", "positions"]
    with h5py.File(f"{basedir}/{sample_name}_{scan_number}_master.h5", "w") as f:
        for group in groups:
            f.create_group(group)
            files = os.listdir(f"{basedir}/{group}")
            if group == "tetramm":
                files = [file for file in files if file.split(".")[-1] == "nc"]
                file = scan_number_in_list(files, str(scan_number))
                string_data = [file.encode("utf-8")]
                dset = f[group].create_dataset("fnames", data=string_data)
            elif group == "mda":
                files = [file for file in files if file.split(".")[-1] == "mda"]
                file = scan_number_in_list(files, str(scan_number))
                string_data = [file.encode("utf-8")]
                dset = f[group].create_dataset("fnames", data=string_data)
            elif group == "flyXRF":
                files = [file for file in files if file.split(".")[-1] == "h5"]
                file = scan_number_in_list(files, str(scan_number))
                f[f"/{group}/{file}"] = h5py.ExternalLink(f"/{group}/{file}", "/entry")
            elif group == "positions":
                files = [file for file in files if file.split(".")[-1] == "h5"]
                file = scan_number_in_list(files, str(scan_number))
                f[f"/{group}/{file}"] = h5py.ExternalLink(f"/{group}/{file}", "/stream")

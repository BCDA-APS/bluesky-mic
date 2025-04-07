"""Miscellaneous utility functions for file operations and scan control."""

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
    """Create a directory if it doesn't exist.

    Parameters:
        directory (str): Path to create.
    """
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
            print(f"Created directory: {directory}")
        except OSError as e:
            print(f"Failed to create directory: {directory} - {e}")
    else:
        print(f"Directory already exists: {directory}")


def mksubdirs(save_path, subdirs=None):
    """Create multiple subdirectories.

    Parameters:
        save_path (str): Base path.
        subdirs (list): List of subdirectories to create.
    """
    if subdirs is None:
        subdirs = []
    for folder in subdirs:
        path = f"{save_path}{folder}"
        mkdir(path)


def pvget(pv):
    """Get PV value using pvget command.

    Parameters:
        pv (str): PV name.
    """
    try:
        cmd = f"pvget {pv}"
        subprocess.getstatusoutput(cmd)
    except subprocess.CalledProcessError:
        pass


def pvput(pv, value):
    """Set PV value using pvput command.

    Parameters:
        pv (str): PV name.
        value: Value to set.
    """
    try:
        cmd = f"pvput {pv} {value}"
        subprocess.getstatusoutput(cmd)
    except subprocess.CalledProcessError:
        pass


def run_subprocess(command_list):
    """Run a subprocess command.

    Parameters:
        command_list (str): Command to execute.

    Returns:
        tuple: Status and output of the command.
    """
    try:
        result = subprocess.getstatusoutput(command_list)
    except subprocess.CalledProcessError as e:
        result = e
        pass
    return result


def pause_scan():
    """Pause the current scan."""
    from ..devices.scan_record import scan2

    wcnt = scan2.wcnt.get()
    if wcnt == 0:
        scan2.wcnt.put(1)
    elif wcnt > 1:
        for _i in range(wcnt - 1):
            scan2.wcnt.put(0)
    print("pausing scan")


def resume_scan():
    """Resume the paused scan."""
    from ..devices.scan_record import scan2

    wcnt = scan2.wcnt.get()
    if wcnt >= 1:
        for _i in range(wcnt):
            scan2.wcnt.put(0)
    print("resuming scan...")


def abort_scan():
    """Abort the current scan."""
    pause_scan()
    from ..devices.scan_record import scan2

    scan2.AbortScan2.put(1)
    scan2.AbortScan2.put(1)
    scan2.AbortScan2.put(1)
    print("aborting scan...")


def scan_number_in_list(lst, partial_str):
    """Find a scan number in a list of strings.

    Parameters:
        lst (list): List of strings to search.
        partial_str (str): Partial string to match.

    Returns:
        str: Matching string from list.
    """
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
    """Create a master HDF5 file linking to various data files.

    Parameters:
        basedir (str): Base directory path.
        sample_name (str): Name of the sample.
        scan_number (str): Scan number.
        groups (list): List of groups to create.
    """
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
                f[group].create_dataset("fnames", data=string_data)
            elif group == "mda":
                files = [file for file in files if file.split(".")[-1] == "mda"]
                file = scan_number_in_list(files, str(scan_number))
                string_data = [file.encode("utf-8")]
                f[group].create_dataset("fnames", data=string_data)
            elif group == "flyXRF":
                files = [file for file in files if file.split(".")[-1] == "h5"]
                file = scan_number_in_list(files, str(scan_number))
                f[f"/{group}/{file}"] = h5py.ExternalLink(f"/{group}/{file}", "/entry")
            elif group == "positions":
                files = [file for file in files if file.split(".")[-1] == "h5"]
                file = scan_number_in_list(files, str(scan_number))
                f[f"/{group}/{file}"] = h5py.ExternalLink(f"/{group}/{file}", "/stream")

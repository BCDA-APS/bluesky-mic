"""Bluesky plan: run_scan()

Usage: ``%run -i run_scan_plan.py``

.. caution:: Assumes this file is not imported, so it does not
    need import statements for all the other library code that
    it calls.  The caller must make those available before this
    code is added by ``%run``.
"""

import time
from typing import Dict
from typing import Union

import bluesky.plan_stubs as bps
import numpy as np
from ophyd.status import Status

from ..devices.positioner_stream import PositionerStream
from ..devices.profile_move import ProfileMove
from ..devices.softgluezynq import SoftGlueZynq
from ..devices.tetramm import TetraMM
from ..devices.xspress3 import Xspress3
from ..utils.misc import create_master_file
from ..utils.misc import mkdir
from ..utils.misc import mksubdirs
from ..utils.misc import pvput
from .trajectories import snake


def run_scan(
    scan_type: str = "fly",
    trajectory: str = "snake",
    loop1: str = "2idsft:m1",
    loop2: str = "2idsft:m2",
    dwell_time: Union[str, float] = "10",
    devices: Dict[str, str] = None,
    sample_name: str = "sample_name",
    pi_directory: str = "/mnt/micdata1/save_dev/",
    comments: str = "",
    l1_center: float = 0,
    l1_size: float = 0.01,
    l1_width: float = 0.5,
    l2_center: float = 0,
    l2_size: float = 0.01,
    l2_width: float = 0.5,
) -> None:
    """Run a scan with the specified parameters.

    Parameters
    ----------
    scan_type : str, optional
        Type of scan to perform, by default "fly"
    trajectory : str, optional
        Trajectory type, by default "snake"
    loop1 : str, optional
        First loop PV, by default "2idsft:m1"
    loop2 : str, optional
        Second loop PV, by default "2idsft:m2"
    dwell_time : Union[str, float], optional
        Dwell time in seconds, by default "10"
    devices : Dict[str, str], optional
        Dictionary of devices to use, by default None
    sample_name : str, optional
        Name of the sample, by default "sample_name"
    pi_directory : str, optional
        Directory to save data, by default "/mnt/micdata1/save_dev/"
    comments : str, optional
        Additional comments, by default ""
    l1_center : float, optional
        Center position of first loop, by default 0
    l1_size : float, optional
        Size of first loop, by default 0.01
    l1_width : float, optional
        Width of first loop, by default 0.5
    l2_center : float, optional
        Center position of second loop, by default 0
    l2_size : float, optional
        Size of second loop, by default 0.01
    l2_width : float, optional
        Width of second loop, by default 0.5
    """
    if devices is None:
        devices = {
            "flyXRF": "XSP3_1Chan:",
            "tetramm": "2idsft:TetrAMM1",
            "profilemove": "2idsft:pm1",
            "softglue": "2idMZ1:",
            "positions": "posvr:",
        }

    """parse parameters"""
    if trajectory == "snake":
        x, y, t = snake(dwell_time, l1_size, l1_center, l2_center, l1_width, l2_width)
    elif trajectory == "raster":
        x, y, t = snake(dwell_time, l1_size, l1_center, l2_center, l1_width, l2_width)
    elif trajectory == "spiral":
        pass
    elif trajectory == "lissajous":
        pass
    elif trajectory == "custom":
        pass

    x = list(np.round(x, 5))
    y = list(np.round(y, 5))
    npts = len(x)
    frequency = 1 / float(dwell_time) / 1000

    folder_name = sample_name.strip("_")
    save_path = f"{pi_directory}{folder_name}/"
    mkdir(save_path)
    device_list = [device for device in devices.keys()]
    subdirs = [
        detector
        for detector in device_list
        if detector in ("flyXRF", "tetramm", "positions", "eiger", "mda", "xmap")
    ]
    mksubdirs(save_path, subdirs)

    """Set up positioners (move to starting pos)"""
    # TODO: of the parameters in loop1-loop4, figure out which are motors somehow
    # or hardcode them in the devices folder and then import them here.

    """trigger source"""
    use_softglue_triggers = "softglue" in devices

    """setup devices"""
    xp3 = None
    tmm = None
    pm1 = None
    sgz = None
    postrm = None

    for device_name, device_prefix in devices.items():
        if device_name == "flyXRF":
            if use_softglue_triggers:
                trigger_mode = 3  # ext trigger
            else:
                trigger_mode = 1  # internal
            xp3 = Xspress3(device_prefix, name="xp3")
            savepath = f"{save_path}{device_name}"
            yield from xp3.setup_xspress3(
                xp3,
                npts,
                sample_name,
                savepath,
                trigger_mode,
                dwell_time,
                reset_counter=False,
            )

        elif device_name == "tetramm":
            if use_softglue_triggers:
                trigger_mode = 1  # ext trigger
            else:
                trigger_mode = 0  # internal
            tmm = TetraMM(device_prefix, name="tmm")
            savepath = f"{save_path}tetramm"
            yield from tmm.setup_tetramm(
                tmm,
                npts,
                sample_name,
                savepath,
                trigger_mode,
                dwell_time,
                reset_counter=False,
            )

        elif device_name == "profilemove":
            pm1 = ProfileMove(device_prefix, name="pm1")
            yield from pm1.setup_profile_move(pm1, x, y, dwell_time)

        elif device_name == "softglue":
            sgz = SoftGlueZynq(device_prefix, name="sgz")
            yield from sgz.setup_SoftGlueZynq(sgz, npts, frequency)

        elif device_name == "positions":
            if xp3 is not None:
                filenumber = "{:05d}".format(xp3.FileNumber - 1)
            else:
                # TODO: figure out a way to increment softglue filenumber whvery
                # time it closes and a way to reset counter.
                msg = (
                    "file number not tracked. Not sure how else to set file name "
                    "if not based on another detector's filenumber"
                )
                print(msg)
                filenumber = "00000"
            postrm = PositionerStream(device_prefix, name="postrm")
            filename = f"positions_{filenumber}.h5"
            postrm.setup_positionstream(filename, f"{save_path}positions")
        else:
            print(f"unknown device: {device_name}")

    """Start executing scan"""
    st = Status()
    print("Done setting up scan, about to start scan")

    def watch_execute_scan(old_value, value, **kwargs):
        # Watch for pm1.EXSC to change from 1 to 0 (when the scan ends).
        if old_value in (1, 2, 3) and value == 0:
            # mark as finished (successfully).
            if xp3 is not None and xp3.DetectorState_RBV in (0, 10):
                st.set_finished()
                print("finished")
                # Remove the subscription.
                pm1.exsc.clear_sub(watch_execute_scan)

    # TODO need some way to check if devices are ready before proceeding.
    # timeout and exit with a warning if something is missing.
    time.sleep(1)
    ready = True

    if ready and all(device is not None for device in (tmm, xp3, postrm, sgz, pm1)):
        # Begin acquiring data from all devices
        yield from bps.mv(
            tmm.Acquire,
            1,  # begin acquiring tetramm
            xp3.Acquire,
            1,  # begin acquiring xspress3
            postrm.start_,
            1,  # begin position stream
            sgz.send_pulses,
            1,  # begin sending pulses
        )
        yield from bps.mv(pm1.exsc, 1)  # begin profile move

        pm1.exsc.subscribe(watch_execute_scan)
        yield from bps.sleep(0.1)  # Small delay to ensure subscription is active
        yield from bps.wait(st)

        # Stop all devices
        yield from bps.mv(
            pm1.abort,
            1,
            tmm.Acquire,
            0,
            tmm.Capture,
            0,
            sgz.enbl_dma,
            0,
            xp3.Capture,
            0,
        )
        if postrm is not None:
            pvput(postrm.stop_.pvname, 1)  # stop position stream

    """Set up masterFile"""
    create_master_file(save_path, sample_name, subdirs)

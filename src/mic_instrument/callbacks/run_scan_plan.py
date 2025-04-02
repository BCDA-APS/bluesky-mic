"""Bluesky plan: run_scan()

Usage: ``%run -i run_scan_plan.py``

.. caution:: Assumes this file is not imported, so it does not
    need import statements for all the other library code that
    it calls.  The caller must make those available before this
    code is added by ``%run``.
"""

import numpy as np

from .trajectories import snake
import time
from ..utils.misc import mkdir, mksubdirs, create_master_file, pvput

def run_scan(
    scan_type="fly",
    trajectory="snake",
    loop1="2idsft:m1",
    loop2="2idsft:m2",
    dwell_time="10",
    devices={
        "flyXRF": "XSP3_1Chan:",
        "tetramm:": "2idsft:TetrAMM1",
        "profilemove": "2idsft:pm1",
        "softglue": "2idMZ1:",
        "positions": "posvr:",
    },
    sample_name="sample_name",
    pi_directory="/mnt/micdata1/save_dev/",
    comments="",
    l1_center=0,
    l1_size=0.01,
    l1_width=0.5,
    l2_center=0,
    l2_size=0.01,
    l2_width=0.5,
):
    """parse parameters"""
    if trajectory == "snake":
        x, y, t = snake(dwell_time, l1_size, m1_center, l2_center, l1_width, m2_width)
    elif trajectory == "raster":
        x, y, t = snake(dwell_time, l1_size, m1_center, l2_center, l1_width, m2_width)
    elif trajectory == "spiral":
        pass
    elif trajectory == "lissajous":
        pass
    elif trajectory == "custom":
        pass

    x = list(np.round(x, 5))
    y = list(np.round(y, 5))
    npts = len(x)
    frequency = 1 / dwell_time / 1000

    folder_name = sample_name.strip("_")
    save_path = f"{pi_directory}{folder_name}/"
    mkdir(save_path)
    devices = [device for device in devices.keys()]
    subdirs = [
        detector
        for detector in devices
        if detector == ("flyXRF" or "tetramm" or "positions" or "eiger" or "mda" or "xmap")
    ]
    mksubdirs(save_path, subdirs)
    """Set up positioners (move to starting pos)"""
    # TODO: of the parameters in loop1-loop4, figure out which are motors somehow or hardcode them in the devices folder and then import them here.

    """trigger source"""
    use_softglue_triggers = "softglue" in devices

    """setup devices"""
    for device in devices.keys():
        if device == "flyXRF":
            if use_softglue_triggers:
                trigger_mode = 3  # ext trigger
            else:
                trigger_mode = 1  # internal
            xp3 = Xspress3(devices[device], name="xp3")
            savepath = f"{save_path}{device}"
            yield from xp3.setup_xspress3(
                xp3,
                npts,
                sample_name,
                savepath,
                trigger_mode,
                dwell_time,
                reset_counter=False,
            )

        elif device == "tetramm":
            if use_softglue_triggers:
                trigger_mode = 1  # ext trigger
            else:
                trigger_mode = 0  # internal
            tmm = TetraMM(devices[device], name="tmm")
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

        elif device == "profilemove":
            pm1 = ProfileMove(devices[device], name="pm1")
            yield from pm1.setup_profile_move(pm1, x, y, dwell_time)

        elif device == "softglue":
            sgz = SoftGlueZynq(devices[device], name="sgz")
            yield from sgz.setup_SoftGlueZynq(sgz, npts, frequency)

        elif device == "positions":
            if "xspress3" in devices:
                filenumber = "{:05d}".format(xp3.FileNumber - 1)
            else:
                # TODO: figure out a way to increment softglue filenumber whvery time it closes and a way to reset counter.
                print(
                    "file number not tracked. Not sure how else to set file name if not based on another detector's filenumber"
                )
            postrm = PositionerStream(devices[device], name="postrm")
            filename = f"positions_{filenumber}.h5"
            postrm.setup_positionstream(filename, f"{save_path}positions")
        else:
            print(f"unknown device: {device}")

    """Start executing scan"""
    st = Status()
    print("Done setting up scan, about to start scan")

    def watch_execute_scan(old_value, value, **kwargs):
        # Watch for scan1.EXSC to change from 1 to 0 (when the scan ends).
        if old_value == (1 or 2 or 3) and value == 0:
            # mark as finished (successfully).
            if xp3.DetectorState_RBV == 0 or 10:
                st.set_finished()
                print("finished")
                # Remove the subscription.
                pm1.exsc.clear_sub(watch_execute_scan)

    # TODO need some way to check if devices are ready before proceeding. timeout and exit with a warning if something is missing.
    # if motors.inpos and pm1.isready and tmm.isready and xp3.isready and sgz.isready and postrm.isready:
    time.sleep(1)
    ready = True

    if ready:
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
        yield from bps.mv(scan.exsc, 1)  # begin profile move

    pm1.exsc.subscribe(watch_execute_scan)  # i think this works
    yield from run_blocking_function(st.wait)

    # #set stop PVs from various devices:
    # yield from bps.mv(pm1.abort, 1,
    #        tmm.Acquire, 0,
    #        tmm.Capture, 0,
    #        sgz.enbl_dma, 0,
    #        xp3.Capture, 0)
    pvput(postrm.stop_.pvname, 1)  # stop position stream

    """Set up masterFile"""
    create_master_file(save_path, sample_name, subdirs)

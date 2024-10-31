"""
Creating a bluesky plan that interacts with Scan Record.
"""

# __all__ = """
#     scan_record_isn
# """.split()

# import logging
# import os
# import time

# import bluesky.plan_stubs as bps
# import pvaccess
# from apstools.plans import run_blocking_function
# from ophyd import EpicsMotor
# from ophyd.status import Status

# from ....src.instrument.devices.scan_record import
# from ..callbacks.trajectories import
# from ..devices.positioner_stream import
# from ..devices.save_data import
# from ..devices.softglue_zynq import
# from ..devices.tetramm import
# from ..devices.xspress3 import
# from ..user.misc import create_master_file

# logger = logging.getLogger(__name__)
# logger.info(__file__)

# print("Creating RE plan that uses scan record")


# def scan_record_isn(
#     scan_type="fly",
#     trajectory="snake",
#     loop1="x_motor",
#     loop2="y_motor",
#     sample_name="sample_name",
#     pi_directory="/mnt/micdata1/save_dev/",
#     comments="",
#     devices=["xspress3", "tetramm", "scanrecord", "softglue", "positions"],#noqa: B006
#     l1_center=0,
#     l1_size=0.01,
#     l1_width=0.5,
#     l2_center=0,
#     l2_size=0.01,
#     l2_width=0.5,
#     dwell_time=10,
#     reset_counter=False,
# ):
#     """parse parameters"""
#     if trajectory == "snake":
#         x, y, t, npts_tot = snake(
#             dwell_time, l1_size, l1_center, l2_center, l1_width, l2_width
#         )
#     elif trajectory == "raster":
#         x, y, npts_line, npts_tot = raster(
#             dwell_time, l1_size, l1_center, l2_center, l1_width, l2_width
#         )
#     elif trajectory == "spiral":
#         pass
#     elif trajectory == "lissajous":
#         pass
#     elif trajectory == "custom":
#         pass

#     dwell = dwell_time / 1000
#     folder_name = sample_name.strip("_")
#     save_path = f"{pi_directory}{folder_name}/"
#     mkdir(save_path)
#     subdirs = []
#     """Set up positioners (move to starting pos)"""
#     # TODO: of the parameters in loop1-loop4, figure out which are motors somehow
#       or hardcode them in the devices folder and then import them here.

#     """setup devices"""
#     if "softglue" in devices:
#         use_softglue_triggers = True
#         trigger2 = sgz.send_pulses.pvname
#         yield from sgz.setup_softgluezynq(sgz, npts_line, dwell)
#     else:
#         use_softglue_triggers = False
#         trigger2 = ""

#     if "scanrecord" in devices:
#         mkdir(os.path.join(save_path, "mda"))
#         subdirs.append("mda")
#         trigger1 = scan1.execute_scan.pvname
#         scanNumber = int(savedata.scanNumber.value)
#         formated_number = "{:04d}".format(scanNumber)
#         yield from scan1.setup_scan1(scan_type, loop1, x, dwell_time)
#         yield from scan2.setup_scan2(
#             scan1, loop2, y, trigger1="", trigger2="", trigger3="", trigger4=""
#         )
#         yield from savedata(savedata, pi_directory, sample_name, reset_counter=False)
#     else:
#         print("scanrecord not specified, cannot scan")
#         return

#     if "xspress3" in devices:
#         mkdir(os.path.join(save_path, "flyXRF"))
#         subdirs.append("flyXRF")
#         if use_softglue_triggers:
#             trigger_mode = 3  # ext trigger
#         else:
#             trigger_mode = 1  # internal
#         savepath = f"{save_path}flyXRF"
#         yield from xp3.setup_xspress3(
#             xp3,
#             npts_tot,
#             sample_name,
#             savepath,
#             dwell,
#             trigger_mode,
#             scanNumber,
#             reset_counter=False,
#         )

#     if "tetramm" in devices:
#         mkdir(os.path.join(save_path, "tetramm"))
#         subdirs.append("tetramm")
#         if use_softglue_triggers:
#             trigger_mode = 1  # ext trigger
#         else:
#             trigger_mode = 0  # internal
#         savepath = f"{save_path}tetramm"
#         yield from tmm1.setup_tetramm(
#             npts_tot,
#             sample_name,
#             save_path,
#             dwell_time,
#             trigger_mode,
#             scanNumber,
#             reset_counter=False,
#         )

#     if "positions" in devices:
#         mkdir(os.path.join(save_path, "positions"))
#         subdirs.append("positions")
#         postrm.setup_positionstream(
#             f"positions_{formated_number}.h5", f"{save_path}positions"
#         )
#     else:
#         print(
#             "file number not tracked. Not sure how else to set file name if not based on another detector's filenumber"  # noqa: E501
#         )

#     """setup motors"""
#     m1 = EpicsMotor(loop1, name="m1")
#     m2 = EpicsMotor(loop2, name="m2")
#     if scan_type == "fly":
#         # TODO: add component to epics motor to get maximum velocity and acceleration
#         # TODO: add and setup additional motors if other loops are motors.. somehow.
#         # set motor velocity = sep_size/dwell_time
#         yield from bps.mv(
#             m1.velocity, 3, m1.acceleration, 0.1, m2.velocity, 3, m2.acceleration, 0.1
#         )
#         m1.move(x[0], wait=True)
#         m2.move(y[0], wait=True)
#         vel = l1_size / dwell  # vel is in mm/s
#         yield from bps.mv(m1.velocity, vel)

#     else:
#         yield from bps.mv(
#             m1.velocity, 3, m1.acceleration, 0.1, m2.velocity, 3, m2.acceleration, 0.1
#         )
#         m1.move(x[0], wait=True)
#         m2.move(y[0], wait=True)

#     """Start executing scan"""
#     print("Done setting up scan, about to start scan")
#     st = Status()

#     # TODO: needs monitoring function incase detectors stall
#       or one of the iocs crashes
#     # monitor trigger count and compare against detector saved frames count. s
#     def watch_execute_scan(old_value, value, **kwargs):
#         # Watch for scan1.EXSC to change from 1 to 0 (when the scan ends).
#         if old_value == 1 and value == 0:
#             # mark as finished (successfully).
#             st.set_finished()
#             # Remove the subscription.
#             scan2.execute_scan.clear_sub(watch_execute_scan)

#     # TODO need some way to check if devices are ready before proceeding. timeout and
#       exit with a warning if something is missing.
#     # if motors.inpos and pm1.isready and tmm.isready and xp3.isready and sgz.isready and postrm.isready:  # noqa: E501
#     time.sleep(2)
#     ready = True
#     while not ready:
#         time.sleep(1)

#     print("executing scan")
#     start_ = pvaccess.Channel(postrm.start_.pvname)
#     start_.put(1)
#     yield from bps.mv(scan2.execute_scan, 1)
#     scan2.execute_scan.subscribe(watch_execute_scan)
#     yield from run_blocking_function(st.wait)
#     stop_ = pvaccess.Channel(postrm.start_.pvname)
#     stop_.put(1)

#     """Set up masterFile"""
#     # print(save_path, sample_name, formated_number, subdirs)
#     create_master_file(save_path, sample_name, formated_number, subdirs)

#     print("end of plan\n")

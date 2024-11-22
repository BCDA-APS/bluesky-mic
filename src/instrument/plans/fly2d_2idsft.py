"""
Creating a bluesky plan that interacts with Scan Record.

EXAMPLE::

    # Load this code in IPython or Jupyter notebook:
    %run -i user/fly2d_2idsft.py

    # # Run the plan with the RunEngine:
    # RE(scan_record2(scanrecord_name = 'scan1', ioc = "2idsft:", m1_name = 'm1',
    #                m1_start = -0.5, m1_finish = 0.5,
    #                m2_name = 'm3', m2_start = -0.2 ,m2_finish = 0.2,
    #                npts = 50, dwell_time = 0.1))
"""

__all__ = """
    fly2d
""".split()

import logging
import time

import bluesky.plan_stubs as bps
from apstools.plans import run_blocking_function
from ophyd import EpicsSignalRO
from ophyd.status import Status

from ..devices.scan_record import ScanRecord
from ..devices.softglue_zynq import sgz
from ..devices.tetramm import tmm1
from ..devices.xspress3 import xp3
from .plan_blocks import count_subscriber
from .plan_blocks import watch_counter

# from instrument.devices.TetraMM import *

logger = logging.getLogger(__name__)
logger.bsdev(__file__)


print("Creating RE plan that uses scan record to do 2D fly scan")
print("Getting list of avaliable detectors")


det_name_mapping = {
    "xrf": xp3,
    "preamp": tmm1,
    "fpga": sgz,
    # "ptycho":"eiger"
}


def selected_dets(**kwargs):
    dets = []
    for k, v in kwargs.items():
        if all([v, isinstance(v, bool)]):
            det_str = k.split("_")[0]
            dets.append(det_name_mapping[det_str])
    return dets


def detectors_init(dets: list):
    for d in dets:
        logger.info(f"Initializing detector {d.name}")
        yield from d.initialize()


def detectors_setup(dets: list, dwell=0, num_frames=0):
    for d in dets:
        logger.info(
            f"Assigning detector {d.name} to have dwell time \
                of {dwell} and # frames of {num_frames}"
        )


def scanrecord_2id_setup(
    outter: ScanRecord,
    inner: ScanRecord,
    x_center: float,
    width: float,
    y_center: float,
    height: float,
):
    """
    Configuring scan record for 2ID beamlines.

    This function assumes x moving motion is in fly mode,
    and y motion is in step mode. Thus the x_center and width
    will be used to set up the inner ScanRecord, while y_center
    and height are used for outter ScanRecord.
    """

    # TODO Need to check what is the desired behavior for AFTER SCAN field
    outter.set_scan_mode("linear")
    outter.set_rel_abs_motion("relative")

    inner.set_scan_mode("fly")
    inner.set_rel_abs_motion("relative")


def fly2d(
    samplename="smp1",
    user_comments="",
    # scanrecord1_pv="2idsft:scan1",
    # scanrecord2_pv="2idsft:scan2",
    scanrecord1_pv="2idsft:scan1",
    scanrecord2_pv="2idsft:scan2",
    width=0,
    height=0,
    x_center=None,
    y_center=None,
    stepsize_x=0,
    stepsize_y=0,
    dwell=0,
    smp_theta=None,
    xrf_on=True,
    ptycho_on=False,
    preamp_on=False,
    fpga_on=False,
    position_stream=False,
    eta=0,
):
    def watch_execute_scan(old_value, value, **kwargs):
        # Watch for scan1.EXSC to change from 1 to 0 (when the scan ends).
        if old_value == 1 and value == 0:
            # mark as finished (successfully).
            st.set_finished()
            # Remove the subscription.
            scanrecord2.execute_scan.clear_sub(watch_execute_scan)
        counter.unsubscribe(watch_counter)


    print(
        f"Creating ophyd object of scan records:\n \
            Outter scan loop PV: {scanrecord1_pv} \n \
            Inner scan loop PV: {scanrecord2_pv} \n"
    )

    counter_pv = scanrecord2_pv + ".CPT"

    counter = EpicsSignalRO(counter_pv, name = "counter")
    scanrecord1 = ScanRecord(scanrecord1_pv)
    scanrecord2 = ScanRecord(scanrecord2_pv)

    if all([scanrecord1.connected, scanrecord2.connected]):
        if "2id" in scanrecord1_pv:
            print(
                f"Based on the {scanrecord1_pv=}, this is beamline 2-ID. \
                  Thus, this plan assumes x motion has a flying motor and \
                  y motion has a stepper motor."
            )

        print("Determining which detectors are selected")
        dets = selected_dets(**locals())
        yield from detectors_init(dets)

        yield from bps.sleep(5)
        print("end of plan")
    else:
        logger.error(
            f"Having issue connecting to scan records: "
            f"{scanrecord1_pv}, {scanrecord2_pv}"
        )

        if xrf_on:
            xp3.initialize()
            dets.append(xp3)
            logger.info("XRF (xpress3) is ready")
        else:
            logger.error(
                "Not able to perform the desired scan due to hardware connection"
            )

    yield from bps.sleep(1)

    # TODO: needs monitoring function incase detectors stall or one of the iocs crashes
    # monitor trigger count and compare against detector saved frames count. s

    # TODO need some way to check if devices are ready before proceeding. timeout and
    #   exit with a warning if something is missing.
    # if motors.inpos and pm1.isready and tmm.isready and xp3.isready and sgz.isready
    # and postrm.isready:

    """Start executing scan"""
    print("Done setting up scan, about to start scan")

    st = Status()
    time.sleep(2)
    ready = True
    while not ready:
        time.sleep(1)

    print("executing scan")

    scanrecord2.execute_scan.subscribe(watch_execute_scan)  # Subscribe to the scan
    # executor

    yield from bps.mv(scanrecord2.execute_scan, 1)  # Start scan
    yield from bps.sleep(1)  # Empirical, for the IOC
    yield from count_subscriber(counter, scanrecord2) # Counter Subscriber

    yield from run_blocking_function(st.wait)

    print("end of plan")


# def scan_record_isn_2(scan_type="fly", trajectory="snake", loop1="2idsft:m1",
#                       loop2="2idsft:m2",
#                       sample_name="sample_name",
#                       xp3_on = False, tetramm_on = False,
#                       softglue_on = False, eiger_on = False,
#                       dets = ["xp3", "tetramm", "eiger"]):  # noqa: B006
#     devices = {v.replace("_on", ""):eval(v.replace("_on", "")) for v in ["xp3_on",
#                                                                         "tetramm_on",
#                                                                         "softglue_on",
#                                                                         "eiger_on"] if eval(v) is True}  # noqa: E501

#     pass


# def scan_record_isn(scan_type="fly",
#                     trajectory="snake",
#                     loop1="2idsft:m1",
#                     loop2="2idsft:m2",
#                     sample_name="sample_name",
#                     pi_directory="/mnt/micdata1/save_dev/",
#                     comments="",
#                     devices=["xspress3",
#                              "tetramm",
#                              "scanrecord",
#                              "softglue",
#                              "positions"],
#                     l1_center=0,
#                     l1_size=0.01,
#                     l1_width=0.5,
#                     l2_center=0,
#                     l2_size=0.01,
#                     l2_width=0.5,
#                     dwell_time=10,
#                     reset_counter=False,
#              ):

#     """parse parameters"""
#     if trajectory == "snake":
#         x, y, t = snake(dwell_time, l1_size, l1_center, l2_center, l1_width, l2_width)
#     elif trajectory == "raster": x, y, npts_line, npts_tot = raster_sr(dwell_time,
#                                       l1_size,
#                                       l1_center,
#                                       l2_center,
#                                       l1_width,
#                                       l2_width)
#     elif trajectory == "spiral":
#         pass
#     elif trajectory == "lissajous":
#         pass
#     elif trajectory == "custom":
#         pass

#     dwell = dwell_time/1000
#     folder_name = sample_name.strip("_")
#     save_path = f"{pi_directory}{folder_name}/"
#     mkdir(save_path)
#     subdirs = []
#     """Set up positioners (move to starting pos)"""
#     #TODO: of the parameters in loop1-loop4, figure out which are motors somehow or
#     #    hardcode them in the devices folder and then import them here.

#     if "softglue" in devices:
#         use_softglue_triggers=True
#         trigger2 = sgz.send_pulses.pvname
#         yield from setup_softgluezynq(sgz, npts_line, dwell)
#     else:
#         use_softglue_triggers=False
#         trigger2=""

#     if "scanrecord" in devices:
#         mkdir(os.path.join(save_path,"mda"))
#         subdirs.append("mda")
#         trigger1 = scan1.execute_scan.pvname
#         scanNumber = int(savedata.scanNumber.value)
#         formated_number = "{:04d}".format(scanNumber)

#         yield from setup_scanrecord(scan1,
#                                     scan2,
#                                     scan_type,
#                                     loop1,
#                                     loop2,
#                                     x,
#                                     y,
#                                     dwell,
#                                     npts_line,
#                                     trigger1=trigger1,
#                                     trigger2=trigger2)
#         yield from setup_savedata(savedata,
#                                 pi_directory,
#                                 sample_name,
#                                 reset_counter=False)
#     else:
#         print("scanrecord not specified, cannot scan")
#         return

#     if "xspress3" in devices:
#         mkdir(os.path.join(save_path,"flyXRF"))
#         subdirs.append("flyXRF")
#         if use_softglue_triggers:
#             trigger_mode = 3 #ext trigger
#         else:
#             trigger_mode = 1 #internal
#         savepath = f"{save_path}flyXRF"

#         yield from setup_xspress3(xp3,
#                                 npts_tot,
#                                 sample_name,
#                                 savepath,
#                                 dwell,
#                                 trigger_mode,
#                                 scanNumber,
#                                 reset_counter=False)

#     if "tetramm"in devices:
#         mkdir(os.path.join(save_path,"tetramm"))
#         subdirs.append("tetramm")
#         if use_softglue_triggers:
#             trigger_mode = 1 #ext trigger
#         else:
#             trigger_mode = 0 #internal
#         savepath = f"{save_path}tetramm"

#         yield from setup_tetramm(tmm,
#                                 npts_tot,
#                                 sample_name,
#                                 savepath,
#                                 dwell,
#                                 trigger_mode,
#                                 scanNumber,
#                                 reset_counter=False)

#     if "positions" in devices:
#         mkdir(os.path.join(save_path,"positions"))
#         subdirs.append("positions")
#         setup_positionstream(f"positions_{formated_number}.h5", f"{save_path}positions")  # noqa: E501
#     else:
#         print("file number not tracked. Not sure how else to set file name if not based on another detector's filenumber")  # noqa: E501

#     """setup motors"""
#     m1 = EpicsMotor(loop1, name="m1")
#     m2 = EpicsMotor(loop2, name="m2")
#     if scan_type == "fly":
#         #TODO: add component to epics motor to get maximum velocity and acceleration
#         #TODO: add and setup additional motors if other loops are motors.. somehow.
#         #set motor velocity = sep_size/dwell_time
#         yield from bps.mv(m1.velocity,
#                         3,
#                         m1.acceleration,
#                         0.1,
#                         m2.velocity,
#                         3,
#                         m2.acceleration,
#                         0.1)
#         m1.move(x[0], wait=True)
#         m2.move(y[0], wait=True)
#         vel = l1_size/dwell #vel is in mm/s
#         yield from bps.mv(m1.velocity, vel)

#     else:
#         yield from bps.mv(m1.velocity,
#                         3,
#                         m1.acceleration,
#                         0.1,
#                         m2.velocity,
#                         3,
#                         m2.acceleration,
#                         0.1)
#         m1.move(x[0], wait=True)
#         m2.move(y[0], wait=True)

#     """Start executing scan"""
#     print("Done setting up scan, about to start scan")
#     st = Status()
#     #TODO: needs monitoring function incase detectors stall or one of teh iocs crashes
#     # monitor trigger count and compare against detector saved frames count. s
#     def watch_execute_scan(old_value, value, **kwargs):
#         # Watch for scan1.EXSC to change from 1 to 0 (when the scan ends).
#         if old_value == 1 and value == 0:
#             # mark as finished (successfully).
#             st.set_finished()
#             # Remove the subscription.
#             scan2.execute_scan.clear_sub(watch_execute_scan)

#     # TODO need some way to check if devices are ready before proceeding. timeout and
#     #   exit with a warning if something is missing.
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


# import sys, bluesky
# RE = bluesky.RunEngine()
# sys.path.append("/home/beams8/USER2IDD/bluesky_gyl/bluesky-mic")
# from src.instrument.plans.fly2d_2idsft import fly2d

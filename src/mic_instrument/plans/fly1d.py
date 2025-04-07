"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)

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
    fly1d
""".split()

import logging
import os

import bluesky.plan_stubs as bps
from apstools.devices import DM_WorkflowConnector
from apstools.plans import run_blocking_function
from ophyd.status import Status

from ..configs.device_config_19id import ptychodus_dm_args
from ..configs.device_config_19id import ptychoxrf_dm_args
from ..configs.device_config_19id import savedata
from ..configs.device_config_19id import scan1
from ..configs.device_config_19id import xrf_dm_args
from ..configs.device_config_19id import xrf_me7
from ..configs.device_config_19id import xrf_me7_hdf
from ..devices.data_management import api
from .dm_plans import dm_submit_workflow_job
from .plan_blocks import count_subscriber
from .plan_blocks import watch_counter

logger = logging.getLogger(__name__)
logger.info(__file__)
SCAN_OVERHEAD = 0.3

print("Creating RE plan that uses scan record to do 1D fly scan")
print("Getting list of avaliable detectors")


det_name_mapping = {
    "simdet": {"cam": None, "hdf": None},
    "xrf_me7": {"cam": xrf_me7, "hdf": xrf_me7_hdf},
    "preamp": {"cam": None, "hdf": None},
    "fpga": {"cam": None, "hdf": None},
    "ptycho": {"cam": None, "hdf": None},
}


def selected_dets(**kwargs):
    dets = {}
    rm_str = "_on"
    for k, v in kwargs.items():
        if all([v, isinstance(v, bool), rm_str in k]):
            det_str = k[: -len(rm_str)]
            dets.update({det_str: det_name_mapping[det_str]})
    #         dets.append(det_name_mapping[det_str])
    return dets


# def detectors_init(dets: list):
#     for d in dets:
#         logger.info(f"Initializing detector {d.name}")
#         yield from d.initialize()


# def detectors_setup(dets: list, dwell=0, num_frames=0):
#     for d in dets:
#         logger.info(
#             f"Assigning detector {d.name} to have dwell time \
#                 of {dwell} and # frames of {num_frames}"
#         )


def fly1d(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
    dwell=0,
    smp_theta=None,
    simdet_on=False,
    xrf_me7_on=True,
    ptycho_on=False,
    preamp_on=False,
    fpga_on=False,
    position_stream=False,
    wf_run=False,
    analysisMachine="mona2",
    eta=0,
):
    ##TODO Close shutter while setting up scan parameters

    print(f"Using {scan1.prefix} as the outter scanRecord")
    if scan1.connected:
        logger.info(f"{scan1.prefix} is connected")

        """Set up scan parameters and get estimated time of a scan"""
        yield from scan1.set_center_width_stepsize(x_center, width, stepsize_x)
        numpts_x = scan1.number_points.value
        eta = numpts_x * dwell * (1 + SCAN_OVERHEAD)
        logger.info(f"Number_points in X: {numpts_x}")
        logger.info(f"Estimated_time for this scan is {eta}")

        """Check which detectors to trigger"""
        logger.info("Determining which detectors are selected")
        dets = selected_dets(**locals())
        # yield from detectors_init(dets)

        ##TODO Create folder for the desire file/data structure
        basepath = savedata.get().file_system
        for det_name, det_var in dets.items():
            det_path = os.path.join(basepath, det_name)
            logger.info(f"Setting up {det_name} to have data saved at {det_path}")
            hdf = det_var["hdf"]
            if hdf is not None:
                hdf.set_filepath(det_path)

        # ##TODO Based on the selected detector, setup DetTriggers in inner scanRecord
        # for i, d in enumerate(dets):
        #     cmd = f"yield from bps.mv(scan1.triggers.t{i}.trigger_pv, {d.Acquire.pvname}"
        #     eval(cmd)

        ##TODO Assign the proper data path to the detector IOCs

        def watch_execute_scan(old_value, value, **kwargs):
            if old_value == 1 and value == 0:
                st.set_finished()
                scan1.execute_scan.clear_sub(watch_execute_scan)

            scan1.number_points_rbv.unsubscribe(watch_counter)

        """Start executing scan"""
        print("Done setting up scan, about to start scan")
        st = Status()
        scan1.execute_scan.subscribe(watch_execute_scan)  # Subscribe to the scan
        # executor

        yield from bps.mv(scan1.execute_scan, 1)  # Start scan
        yield from bps.sleep(1)  # Empirical, for the IOC
        yield from count_subscriber(
            scan1.number_points_rbv, scan1.number_points.get()
        )  # Counter Subscriber
        yield from run_blocking_function(st.wait)

        #############################
        # START THE APS DM WORKFLOW #
        #############################

        if wf_run:
            dm_workflow = DM_WorkflowConnector(name=samplename, labels=("dm",))

            if all([xrf_me7_on, ptycho_on]):
                WORKFLOW = "ptycho-xrf"
                argsDict = ptychoxrf_dm_args.copy()
            elif xrf_me7_on:
                WORKFLOW = "xrf-maps"
                argsDict = xrf_dm_args.copy()
            else:
                WORKFLOW = "ptychodus"
                argsDict = ptychodus_dm_args.copy()

            ##TODO Modify argsDict accordingly based on the scan parameters
            argsDict["analysisMachine"] = analysisMachine

            yield from dm_submit_workflow_job(WORKFLOW, argsDict)
            logger.info(f"{len(api.listProcessingJobs())=!r}")

        logger.info("DM workflow Finished!")
        print("end of plan")

    else:
        print(f"Having issue connecting to scan record: {scan1.prefix}")

    # yield from bps.sleep(1)
    # print("end of plan")

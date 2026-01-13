""" Bluesky plan for a 1D step scan.

"""

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import oregistry
from s2idd_uprobe.utils.fly import get_next_file_name
from s2idd_uprobe.plans.toggle_usercalc import disable_usercalc, enable_usercalc
from s2idd_uprobe.utils.fly import validate_scan_parameters
from s2idd_uprobe.plans.stepscan_core import _step1d, _common_stepscan_cleanup, _common_stepscan_setup
import numpy as np
import logging
from mic_common.utils.timer_decorator import loop_timer_context
from s2idd_uprobe.utils.param_capture import capture_params
from s2idd_uprobe.utils.nexus_bps_func import save_ophyd_value

logger = logging.getLogger(__name__)


samx = oregistry["samx"]
samy = oregistry["samy"]
samz = oregistry["samz"]
savedata = oregistry["savedata"]


def get_positioner(positioner):
    if positioner == "samx":
        return samx
    elif positioner == "samy":
        return samy
    elif positioner == "samz":
        return samz
    else:
        raise ValueError(f"Positioner {positioner} not supported")


def step1d(
    samplename="smp1",
    user_comments="",
    positioner="samx",
    length=0,
    center=None,
    stepsize=0,
    dwell_ms=0,
    preamp1_on=True,
    xrf_on=True,
    preamp2_on=False,
):

    """Capture the input plan parameters"""
    plan_args = capture_params(step1d, **locals())
    
    """Disable usercalc"""
    yield from disable_usercalc()

    """Get the positioner ophyd object"""
    pos_ophyd = get_positioner(positioner)

    """Check input parameters and detector status. Turn off xrf_netcdf file plugin"""
    logger.info("Validating scan parameters and detector status")
    validate_scan_parameters(stepsize_x=stepsize, dwell_ms=dwell_ms)

    """Construct the scan points and move to the starting position. If positioner is samx, set samx motor speed to its max speed"""
    logger.info("Constructing the scan points and moving to the starting position")
    if center is None:
        center = pos_ophyd.position
    pos_arr = np.arange(center - length/2, center + length/2, stepsize)
    yield from bps.mv(pos_ophyd, pos_arr[0])
    if positioner == "samx":
        x_motor_retrace = pos_ophyd.get_max_velocity()
        yield from bps.mv(pos_ophyd.velocity, x_motor_retrace)

    """Setup detectors and file I/O"""
    total_pts = len(pos_arr)
    filename = get_next_file_name(savedata)
    devices_dict, fileplugins_dict = yield from _common_stepscan_setup(
        xrf_on, preamp1_on, preamp2_on, total_pts, dwell_ms, filename
    )
    xrf = devices_dict["xrf"]
    sis3820 = devices_dict["sis3820"]

    """Construct the metadata"""
    md = {"plan_args": plan_args,
          "shape": (total_pts,),
          "extents": ((pos_arr[0], pos_arr[-1]),),
          }

    """Start the scan"""
    @bpp.run_decorator(md=md)
    def inner_step1d():
        logger.info("Starting the scan")
        with loop_timer_context(f"Data saved to {filename}", total_iterations=total_pts) as timer:
            print("Open shutter")
            yield from savedata.set_next_scan_number(savedata.next_scan_number.get() + 1)
            yield from _step1d(xrf, sis3820, pos_ophyd, pos_arr, timer, [pos_ophyd])

    """Stop the scan"""
    yield from _common_stepscan_cleanup(devices_dict)

            
            

    



    

""" Bluesky plan for a 2D step scan.

"""

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import oregistry
from s2idd_uprobe.utils.fly import get_next_file_name
from s2idd_uprobe.plans.toggle_usercalc import disable_usercalc, enable_usercalc
from s2idd_uprobe.utils.fly import validate_scan_parameters
from s2idd_uprobe.plans.stepscan_core import (
    _step1d_xrfnc,
    _common_stepscan_cleanup,
    _common_stepscan_setup,
)
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


def step2d(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
    height=0,
    y_center=None,
    stepsize_y=0,
    dwell_ms=0,
    sample_z=None,
    inc_eng=None,
    adjust_zp=False,
    preamp2_on=False,
    preamp1_on=True,
    xrf_on=True,
    snake_scan=False,
):
    """Capture the input plan parameters"""
    plan_args = capture_params(step2d, **locals())

    """Disable usercalc"""
    yield from disable_usercalc()

    """Setup the sample z, x, and y position"""
    if sample_z is not None:
        yield from bps.mv(samz, sample_z)
    if x_center is None:
        yield from bps.mv(samx, samx.position - width / 2)
    if y_center is not None:
        yield from bps.mv(samy, samy.position - height / 2)

    """Check input parameters and detector status. Turn off xrf_netcdf file plugin"""
    logger.info("Validating scan parameters and detector status")
    validate_scan_parameters(
        stepsize_x=stepsize_x, stepsize_y=stepsize_y, width=width, height=height, dwell_ms=dwell_ms
    )

    """Construct the scan points and set samx motor speed to its max speed"""
    logger.info("Constructing the scan points and setting samx motor speed to its max speed")
    xarr = np.arange(x_center - width / 2, x_center + width / 2, stepsize_x)
    yarr = np.arange(y_center - height / 2, y_center + height / 2, stepsize_y)
    x_motor_retrace = samx.get_max_velocity()
    yield from bps.mv(samx.velocity, x_motor_retrace)

    """Setup detectors and file I/O"""
    numpts_x = len(xarr)
    numpts_y = len(yarr)
    total_pts = numpts_x * numpts_y
    filename = get_next_file_name(savedata)
    devices_dict, fileplugins_dict = yield from _common_stepscan_setup(
        xrf_on, preamp1_on, preamp2_on, numpts_x, dwell_ms, filename
    )
    devices = [det for k, det in devices_dict.items()]
    fileplugins = [fileplugin for k, fileplugin in fileplugins_dict.items()]

    # Get detector objects from the dictionary
    xrf = devices_dict["xrf"]
    sis3820 = devices_dict["sis3820"]
    md = {
        "plan_args": plan_args,
        "shape": (len(yarr), len(xarr)),
        "extents": ((xarr[0], xarr[-1]), (yarr[0], yarr[-1])),
    }

    # @bpp.run_decorator(md=md)
    def _step2d():
        """Start the scan"""
        logger.info("Starting the scan")
        with loop_timer_context(f"Data saved to {filename}", total_iterations=total_pts) as timer:
            for i, y in enumerate(yarr):
                yield from bps.mv(samy, y)

                for det in devices:
                    if det.name == "sis3820":
                        yield from det.set_erase_start(1)
                    elif det.name == "tmm1":
                        yield from det.start_acquire()
                    elif det.name == "tmm2":
                        yield from det.start_acquire()

                # try:
                #     yield from save_ophyd_value(samy)
                # except Exception as e:
                #     logger.error(f"Error saving ophyd value for samy: {e}")
                #     continue
                if i == 0:
                    print("Open shutter")
                    yield from savedata.set_next_scan_number(savedata.next_scan_number.get() + 1)

                # yield from _step1d(xrf, sis3820, samx, xarr, timer, [samx, samy],
                #                 y_index=i)
                yield from _step1d_xrfnc(
                    devices, fileplugins, samx, xarr, timer, [samx, samy], y_index=i
                )

                # stop xrf_netcdf file plugin
                for fileplugin in fileplugins:
                    if fileplugin is not None and fileplugin.name == "xrf_netcdf":
                        yield from fileplugin.set_capture("Done")

    yield from _step2d()

    """Stop the scan"""
    yield from _common_stepscan_cleanup(devices_dict)

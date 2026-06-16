"""
Keithley 2400 Moxa plans.

@author: yluo(grace227)
"""

__all__ = """
    jv_sweep
    mspt
    pulsatile_therapy
    mppt
""".split()

import logging, os
from s2idd_uprobe.user.keithley2400_moxa import Keithley2400
from apsbits.core.instrument_init import oregistry
from mic_common.utils.param_capture import capture_params
import bluesky.preprocessors as bpp
import bluesky.plan_stubs as bps

logger = logging.getLogger(__name__)
savedata = oregistry["savedata"]
keithley = oregistry["keithley"]
nxwriter = oregistry["nxwriter"]

def jv_sweep(
    fname: str = "jv_sweep",
    attempt: int = 1,
    max_attempts: int = 2,
    compliance_current: float = 0.003,
    jv_duration: float = 50.0,
    n_value: float = 1.05,
    area: float = 0.0625,
    initial_pce_input: float = 100.0,
    jv_start: float = -0.1,
    jv_end: float = 1.3,
    voltage_step: float = 0.01,
    number_of_sweeps: int = 2,
):

    plan_args = capture_params(jv_sweep, **locals())

    if "fname" in plan_args:
        keithley_dir = os.path.join(savedata.get_storage_path(), 'keithley')
        os.makedirs(keithley_dir, exist_ok=True)
        plan_args["file_path"] = os.path.join(keithley_dir, plan_args.pop("fname") + ".csv")
    logger.info(f"File path: {plan_args['file_path']}")

    nxwriter.keithley_scan = True
    md = {"plan_args": plan_args}
    @bpp.run_decorator(md=md)
    def _jv_sweep():
        keithley.open()
        keithley.set_compliance_current(compliance_current)
        keithley.run_jv_sweep(**plan_args)
        keithley.reset()
        keithley.close()
        yield from bps.null()

    yield from _jv_sweep()
    nxwriter.keithley_scan = False

def mppt(
    fname: str = "jv_sweep",
    attempt: int = 1,
    max_attempts: int = 2,
    compliance_current: float = 0.003,
    jv_duration: float = 50.0,
    n_value: float = 1.05,
    area: float = 0.0625,
    initial_pce_input: float = 100.0,
    jv_start: float = -0.1,
    jv_end: float = 1.3,
    voltage_step: float = 0.01,
    number_of_sweeps: float = 2,
    mppt_duration_min: float = 1,
    mppt_stabilization_time_min: float = 0.05,
):
    plan_args = capture_params(mppt, **locals())

    if "fname" in plan_args:
        keithley_dir = os.path.join(savedata.get_storage_path(), 'keithley')
        os.makedirs(keithley_dir, exist_ok=True)
        plan_args["file_path"] = os.path.join(keithley_dir, plan_args.pop("fname") + ".csv")
    logger.info(f"File path: {plan_args['file_path']}")


    nxwriter.keithley_scan = True
    md = {"plan_args": plan_args}
    @bpp.run_decorator(md=md)
    def _mppt():
        keithley.open()
        keithley.set_compliance_current(compliance_current)
        keithley.run_jv_sweep(plan_args['file_path'], attempt, max_attempts=max_attempts,
                              jv_duration=jv_duration, n_value=n_value, area=area,
                              initial_pce_input=initial_pce_input, jv_start=jv_start,
                              jv_end=jv_end, voltage_step=voltage_step, number_of_sweeps=number_of_sweeps)
        keithley.run_mppt(plan_args['file_path'], mppt_duration_min * 60, area=area,
                          stabilization_time=mppt_stabilization_time_min * 60)
        keithley.reset()
        keithley.close()
        yield from bps.null()

    yield from _mppt()
    nxwriter.keithley_scan = False


def mspt(
    fname: str = "jv_sweep",
    attempt: int = 1,
    max_attempts: int = 2,
    compliance_current: float = 0.003,
    jv_duration: float = 50.0,
    n_value: float = 1.05,
    area: float = 0.0625,
    initial_pce_input: float = 100.0,
    jv_start: float = -0.1,
    jv_end: float = 1.3,
    voltage_step: float = 0.01,
    number_of_sweeps: float = 2,
    mspt_duration_min: float = 1,
    mspt_stabilization_time_min: float = 0.05,
    delta_v_threshold: float = 0.5
):
    plan_args = capture_params(mspt, **locals())

    if "fname" in plan_args:
        keithley_dir = os.path.join(savedata.get_storage_path(), 'keithley')
        os.makedirs(keithley_dir, exist_ok=True)
        plan_args["file_path"] = os.path.join(keithley_dir, plan_args.pop("fname") + ".csv")
    logger.info(f"File path: {plan_args['file_path']}")


    nxwriter.keithley_scan = True
    md = {"plan_args": plan_args}
    @bpp.run_decorator(md=md)
    def _mspt():
        keithley.open()
        keithley.set_compliance_current(compliance_current)
        keithley.run_jv_sweep(plan_args['file_path'], attempt, max_attempts=max_attempts,
                              jv_duration=jv_duration, n_value=n_value, area=area,
                              initial_pce_input=initial_pce_input, jv_start=jv_start,
                              jv_end=jv_end, voltage_step=voltage_step, number_of_sweeps=number_of_sweeps)
        keithley.run_mspt(plan_args['file_path'], mspt_duration_min * 60, area=area,
                          stabilization_time=mspt_stabilization_time_min * 60,
                          delta_v_threshold=delta_v_threshold)
        keithley.reset()
        keithley.close()
        yield from bps.null()

    yield from _mspt()
    nxwriter.keithley_scan = False
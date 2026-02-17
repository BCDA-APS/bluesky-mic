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
    jv_duration: float = 50.0,
    n_value: float = 0.95,
    area: float = 0.0625,
    initial_pce_input: float = 100.0,
    jv_start = -0.1,
    jv_end = 1.3,
    voltage_step = 0.01,
    number_of_sweeps = 2,
):

    plan_args = capture_params(jv_sweep, **locals())

    scan_id = None
    try:
        scan_id = savedata.next_scan_number.get()
        logger.info(f"Scan id: {scan_id}")
    except Exception as e:
        logger.error(f"Error getting scan id: {e}")
        scan_id = None

    if "fname" in plan_args:
        keithley_dir = os.path.join(savedata.get_storage_path(), 'keithley')
        os.makedirs(keithley_dir, exist_ok=True)
        plan_args["file_path"] = os.path.join(keithley_dir, plan_args.pop("fname") + f"_scan_{scan_id:04d}.csv")
    logger.info(f"File path: {plan_args['file_path']}")

    nxwriter.keithley_scan = True
    md = {"plan_args": plan_args, "scan_id": scan_id}
    @bpp.run_decorator(md=md)
    def _jv_sweep():
        keithley.open()
        keithley.run_jv_sweep(**plan_args)
        keithley.close()
        yield from bps.null()

    yield from _jv_sweep()
    nxwriter.keithley_scan = False

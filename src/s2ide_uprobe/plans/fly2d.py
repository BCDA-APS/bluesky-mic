"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    fly2d
""".split()

import logging
from apsbits.utils.controls_setup import oregistry
from s2ide_uprobe.utils.scan_monitor import execute_scan_2d
# from mic_common.utils.scan_monitor import execute_scan_2d
from mic_common.plans.generallized_scan_1d import generalized_scan_1d
from bluesky import plan_stubs as bps  
from apsbits.utils.config_loaders import get_config
from s2ide_uprobe.utils.usercalc_lib import hydra_config, sis3820_config, xrf_config
from ophyd.status import Status
from apstools.plans import run_blocking_function

logger = logging.getLogger(__name__)
logger.info(__file__)
SCANNUM_DIGITS = 4

samx = oregistry["sim1"]
samy = oregistry["sim2"]
# fscan1 = oregistry["scan2"]
# fscanh = oregistry["scan1"]

# samx = oregistry["samx"]
# samy = oregistry["samy"]
fscan1 = oregistry["fscan1"]
fscanh = oregistry["fscanh"]
fscanh_samx = oregistry["fscanh_samx"]
flydwell = oregistry["flydwell"]
savedata = oregistry["savedata"]
hydra = oregistry["hydra"]
sis3820 = oregistry["sis3820"]
xrf = oregistry["xrf"]
xrf_netcdf = oregistry["xrf_netcdf"]
iconfig = get_config()
scan_overhead = iconfig.get("SCAN_OVERHEAD")
xmap_buffer = iconfig.get("XMAP", "BUFFER")


def fly2d(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
    height=0,
    y_center=None,
    stepsize_y=0,
    dwell=0,
    smp_theta=None,
    xrf_on=True,
    ptycho_on=False,
    preamp_on=False,
    position_stream=False,
    wf_run=False,
    analysisMachine="mona2",
):
    """2D Bluesky plan that drives the x- and y- sample motors in flying mode using
    ScanRecord
    
    The plan will drive samx and samy to the requested x_center and y_center, 
    and then perform a relative scan in the x and y directions.

    Parameters
    ----------
    samplename: 
        Str: The name of the sample
    user_comments: 
        Str: The user comments for the scan
    width:
        Float: The width of the scan
    x_center:
        Float: The center of the scan in the x direction. Default is None which uses the current position of samx
    stepsize_x:
        Float: The step size in the x direction
    height:
        Float: The height of the scan
    y_center:
        Float: The center of the scan in the y direction. Default is None which uses the current position of samy
    stepsize_y:
        Float: The step size in the y direction
    dwell:
        Float: The dwell time in the scan
    smp_theta:
        Float: The theta of the sample
    xrf_on:
        Bool: Whether to collect XRF data
    ptycho_on:
        Bool: Whether to collect Ptycho data
    preamp_on:
        Bool: Whether to collect Preamp data
    position_stream:
        Bool: Whether to collect position stream data
    wf_run:
        Bool: Whether to run the workflow
    analysisMachine:
        Str: The name of the analysis machine
    """

    ##TODO Close shutter while setting up scan parameters

    """Move to the requested x- and y- centers"""
    logger.info("Moving to the requested x- and y- centers")
    if x_center is not None:
        yield from bps.mv(samx, x_center)
    if y_center is not None:
        yield from bps.mv(samy, y_center)

    """Set up the inner loop scan record based on the scan types and parameters"""
    yield from bps.mv(fscanh.positioners.p1.abs_rel, "absolute".upper())
    yield from generalized_scan_1d(fscanh, samx, savedata, scan_overhead=scan_overhead,
                                    scanmode="FLY", x_center=x_center, width=width, 
                                    stepsize_x=stepsize_x, dwell=dwell)
    # yield from generalized_scan_1d(fscanh, fscanh_samx, savedata, scan_overhead=scan_overhead,
    #                                 scanmode="FLY", x_center=x_center, width=width, 
    #                                 stepsize_x=stepsize_x, dwell=dwell)
    # yield from fscanh.set_positioner_readback("")

    """Set up the outter loop scan record"""
    yield from bps.mv(fscan1.positioners.p1.abs_rel, "relative".upper())
    yield from generalized_scan_1d(fscan1, samy, savedata, scan_overhead=scan_overhead,
                                   scanmode="LINEAR", x_center=0, width=height, 
                                   stepsize_x=stepsize_y, dwell=dwell)

    # """Set up the hydra (motor controller)"""
    # yield from hydra_config(hydra, fscanh)

    # """Assign the per-pixel dwell time"""
    # logger.info(f"Setting per-pixel dwell time ({flydwell.pvname}) to {dwell} ms")
    # yield from bps.mv(flydwell, dwell)

    # """Set up SIS3820"""
    # yield from sis3820_config(sis3820, fscanh)

    # """Set up XMAP and XRF_NetCDF"""
    # savedata.update_next_file_name()
    # yield from xrf_config(xrf, xrf_netcdf, fscanh, savedata.next_file_name)

    st = Status()

    def outter_counter_callback(value, old_value, **kwargs):
        logger.info(f"Outter counter callback called with value {value} and old_value {old_value}")
        # if value >= 1:
        logger.info(f"Sending erase start signal to sis3820")
            # yield from sis3820.set_erase_start(1)
        logger.info(f"Sending parameters to hydra")
            # yield from hydra.set_send_parameters(1)

    def watch_execute_scan(old_value, value, **kwargs):
        """Monitor scan execution.

        Parameters:
            old_value (int): Previous execution value.
            value (int): Current execution value.
            **kwargs: Additional keyword arguments.
        """
        if old_value == 1 and value == 0:
            st.set_finished()
            logger.info(f"FINISHED: ScanMonitor.st {st}")



    """Start executing scan"""
    # yield from bps.sleep(2)
    savedata.update_next_file_name()
    fscan1.number_points_rbv.subscribe(outter_counter_callback)
    yield from bps.mv(fscan1.execute_scan, 1)  # Start scan
    yield from run_blocking_function(st.wait)
    # yield from execute_scan_2d(fscanh, fscan1, scan_name=savedata.next_file_name, 
    #                            print_outter_msg=True)



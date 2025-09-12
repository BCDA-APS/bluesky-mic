"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    fly2d_scanrecord
""".split()

import logging
from apsbits.utils.controls_setup import oregistry
from mic_common.utils.scan_monitor import execute_scan_2d
from mic_common.plans.generallized_scan_1d import generalized_scan_1d
from bluesky import plan_stubs as bps
from apsbits.utils.config_loaders import get_config
from s2ide_uprobe.utils.usercalc_lib import hydra_config, sis3820_config, xrf_config
from ophyd.status import Status
from apstools.plans import run_blocking_function
from s2ide_uprobe.plans.before_after_fly import setup_flyscan_ptycho_triggers, setup_flyscan_XRF_triggers
from apsbits.utils.config_loaders import get_config

logger = logging.getLogger(__name__)
logger.info(__file__)

fscan1 = oregistry["scan2"]
fscanh = oregistry["scan1"]
samx = oregistry["samx"]
samy = oregistry["samy"]
samtheta = oregistry["samtheta"]
fscan1 = oregistry["fscan1"]
fscanh = oregistry["fscanh"]
fscanh_samx = oregistry["fscanh_samx"]
flydwell = oregistry["flydwell"]
savedata = oregistry["savedata"]
hydra = oregistry["hydra"]
sis3820 = oregistry["sis3820"]
xrf = oregistry["xrf"]
ptycho = oregistry["ptycho"]
ptycho_hdf = oregistry["ptycho_hdf"]
xrf_netcdf = oregistry["xrf_netcdf"]
usercalc_xmap_filename = oregistry["usercalc_xmap_filename"]

iconfig = get_config()
scan_overhead = iconfig.get("SCAN_OVERHEAD")
xmap_buffer = iconfig.get("XMAP", "BUFFER")
netcdf_delimiter = iconfig.get("FILE_DELIMITER")
det_foldername = {"xrf": "flyXRF", "preamp1": "tetramm", "preamp2": "tetramm2", "ptycho": "ptycho"}


def fly2d_scanrecord(
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
    ptycho_exp_factor=1,
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
    ptycho_exp_factor:
        Float: The exposure factor for the Ptycho detector
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

    """Disable the usercalc that used in scan record"""
    usercalc_xmap_filename.set(0)

    """Move sample theta to the requested angle"""
    if smp_theta is not None:
        yield from bps.mv(samtheta, smp_theta)
        yield from bps.sleep(1)
        logger.info(f"Moved sample theta to {smp_theta} degrees")

    """Move to the requested x- and y- positions"""
    yield from bps.mv(samx, x_center)
    yield from bps.mv(samy, y_center)

    """Set up scan record based on the scan types and parameters"""
    yield from generalized_scan_1d(
        scanrecord=fscanh,
        scanmode="FLY",
        x_center=x_center,
        width=width,
        stepsize_x=stepsize_x,
        dwell=dwell,
        savedata=savedata,
    )
    yield from fscanh.set_positioner_drive(f"{fscanh_samx.pvname}")
    yield from fscanh.set_positioner_readback("")

    """Set up the outter loop scan record"""
    yield from fscan1.set_scan_mode("linear")
    yield from fscan1.set_positioner_drive(f"{samy.prefix}.VAL")
    yield from fscan1.set_positioner_readback(f"{samy.prefix}.RBV")

    # check if the scan movement is relative or absolute
    scan_movement = fscan1.scan_movement.enum_strs[fscan1.scan_movement.get()]
    if scan_movement == "RELATIVE":
        yield from bps.mv(samy, y_center)
        yield from fscan1.set_center_width_stepsize(0, height, stepsize_y)
    else:
        yield from fscan1.set_center_width_stepsize(y_center, height, stepsize_y)

    """Assign the per-pixel dwell time"""
    logger.info(f"Setting per-pixel dwell time ({flydwell.pvname}) to {dwell} ms")
    yield from bps.mv(flydwell, dwell)

    """Update the next file name for the detector file plugin"""
    savedata.update_next_file_name()
    next_file_name = savedata.next_file_name
    filename = next_file_name.replace(".mda", "_XMAP")

    """Initialize detectors with desired pts, exposure time and file writer """
    if sis3820.connected:
        # Set up triggers for FLY scans, sis3820 will be sending out pulses. The number of pulses is numpts_x - 2
        numpts_x = fscanh.number_points.value
        num_pulses = numpts_x - 2

        if all([xrf_on, xrf.connected, xrf_netcdf.connected]):
            num_capture = 0  # When it's zero, the num_capture won't be overwritten
            yield from setup_flyscan_XRF_triggers(fscanh, xrf, xrf_netcdf, sis3820, num_pulses)
            yield from xrf.before_flyscan(num_pulses)

            yield from xrf_netcdf.setup_file_writer(
                savedata,
                det_foldername["xrf"],
                num_capture,
                filename=filename,
                beamline_delimiter=netcdf_delimiter,
            )

            yield from xrf_netcdf.set_capture("capturing")

        if ptycho_on:
            yield from setup_flyscan_ptycho_triggers(fscan1, fscanh, ptycho, eiger_filewriter=ptycho_hdf)
            yield from ptycho.scan_init(dwell / 1e3, num_pulses, ptycho_exp_factor)

            if ptycho_hdf is not None:
                # If an hdf5 file plugin is used, we need to disable the Eiger's default file writer.
                yield from ptycho.set_file_writer_enable("Disable")

                next_file_number_str = str(savedata.next_scan_number.get()).zfill(3)
                eiger_filename = f"fly{next_file_number_str}_data"
                yield from ptycho_hdf.setup_file_writer(
                    savedata,
                    "ptycho",
                    num_pulses,
                    filename=eiger_filename,
                    beamline_delimiter=netcdf_delimiter,
                    next_filenum=1,
                )

    """Start executing scan"""

    # yield from bps.sleep(1)
    yield from execute_scan_2d(fscanh, fscan1, scan_name=savedata.next_file_name, print_outter_msg=True)

    # Restore the previous scan record triggers
    logger.info("Restoring the previous scan record triggers before exiting the plan")
    yield from bps.sleep(2)

    if ptycho_on:
        yield from fscan1.restore_detTriggers()

    """Enable the usercalc that used in scan record"""
    usercalc_xmap_filename.set(1)

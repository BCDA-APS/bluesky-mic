"""
A collection of functions to help with handling conditions and update PV values during scans

"""

import logging
from apsbits.utils.controls_setup import oregistry
from apsbits.utils.config_loaders import get_config
import numpy as np

logger = logging.getLogger(__name__)
logger.info(__file__)

fscan1 = oregistry["fscan1"]
fscanh = oregistry["fscanh"]
sis3820 = oregistry["sis3820"]
samx = oregistry["samx"]
iconfig = get_config()
xmap_buffer = iconfig.get("XMAP", "BUFFER")


def stop_dets(sis3820, xrf, xrf_netcdf):
    """
    Stop all detectors
    Parameters:
        sis3820: SIS3820
            The SIS3820 device
        xrf: XRF
            The XRF device
        xrf_netcdf: XRF_NetCDF
            The XRF_NetCDF fileplugin
    """
    yield from sis3820.set_stop_all(1)
    yield from xrf.set_stop_all(1)
    yield from xrf_netcdf.set_capture("done")       



def check_xstage_stuck(elapsed_realtime = 1, sis3820_current_channel = 0):
    """
    Check if the xstage is stuck

    Parameters:
        elapsed_realtime: float
            The elapsed realtime in seconds
        sis3820_current_channel: int
            The current channel of the sis3820

    Returns:
        bool: True if the xstage is stuck, False otherwise
    """
    sis3820_acquiring = sis3820.acquiring.get()
    fscan1_running = fscan1.execute_scan.get()
    samx_done_moving = samx.motor_done_move.get()
    sis3820_current_channel = sis3820.current_channel.get()
    sis3820_elapsed_real = sis3820.elapsed_real.get()

    if all([
        sis3820_acquiring,
        fscan1_running,
        samx_done_moving,
        sis3820_current_channel == sis3820_current_channel,
        sis3820_elapsed_real > elapsed_realtime,
    ]):
        return True
    else:
        return False


def unstuck_xstage():
    """
    Unstuck the xstage by moving to the start or end position 
    depending on which is closer
    """
    start_position = fscan1.start_position.get()
    end_position = fscan1.end_position.get()
    curr_position = samx.position.get()
    distance_to_start = abs(start_position - curr_position)
    distance_to_end = abs(end_position - curr_position)

    if distance_to_start < distance_to_end:
        samx.move(end_position)
        logger.info(f"Unstuck xstage: Moving to end position {end_position}")
    else:
        samx.move(start_position)
        logger.info(f"Unstuck xstage: Moving to start position {start_position}")



def sis3820_config(sis3820, fscan1):
    """Set up SIS3820 based on the fscan1 parameters
    
    Parameters:
        sis3820: SIS3820
            The SIS3820 device
        fscan1: FScan1
            The linear scan record
    """

    total_points = fscan1.number_points.get()
    total_trigger = total_points - 2
    yield from sis3820.set_stop_all(1)
    yield from sis3820.set_num_ch_used(total_trigger)


def xrf_config(xrf, xrf_netcdf, scanrecord, fname, xmap_buffer_size=xmap_buffer):
    """Set up XRF and XRF_NetCDF based on parameters in fscanh
    
    Parameters:
        xrf: XRF
            The XRF device
        xrf_netcdf: XRF_NetCDF
            The XRF_NetCDF fileplugin
        scanrecord: ScanRecord, usually the inner scan record for 2D scans
            The scanrecord to coordinate the scans
        fname: str
            The name of the file to write to
    """
    total_points = fscanh.number_points.get()
    total_trigger = total_points - 2

    # Check if the scanrecord is flying or stepping
    scan_mode = scanrecord.scan_mode.enum_strs[scanrecord.scan_mode.get()]
    if scan_mode == "FLY":
        # For fly scan, we need to configure XMAP and XRF_NetCDF
        num_buffer = int(np.ceil(total_trigger / xmap_buffer_size))
        yield from xrf_netcdf.set_capture("done")  # Stop capture
        yield from xrf_netcdf.set_filename(fname)  # Set the filename
        yield from xrf_netcdf.set_filenumber(0)    # Set the next filenumber to 0
        yield from xrf_netcdf.set_num_capture(num_buffer)
        yield from xrf.flyscan_before(total_trigger)
    else:
        # For step scan, we don't save netcdf files and just need to configure XMAP
        yield from xrf.stepscan_before()



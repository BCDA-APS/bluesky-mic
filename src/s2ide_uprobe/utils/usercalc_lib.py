"""
A collection of functions to help with handling conditions and update PV values during scans

"""

import logging
from apsbits.utils.controls_setup import oregistry
import numpy as np

logger = logging.getLogger(__name__)
logger.info(__file__)

fscan1 = oregistry["fscan1"]
fscanh = oregistry["fscanh"]
sis3820 = oregistry["sis3820"]
samx = oregistry["samx"]


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



def hydra_config(hydra, fscanh):
    """Set up Hydra (motor controller) based on the fscanh parameters
    
    Parameters:
        hydra: Hydra
            The Hydra device
        fscanh: FScanH
            The fly scan record
    """
    stepsize = fscanh.stepsize.get()
    end_position = fscanh.end_position.get()
    start_position = fscanh.start_position.get()
    total_trigger = fscanh.number_points.get()

    yield from hydra.set_start_position(start_position+stepsize)
    yield from hydra.set_end_position(end_position)
    yield from hydra.set_total_trigger(total_trigger)
    yield from hydra.set_mode("Equidistant / Standard")
    yield from hydra.set_send_parameters(1)


def sis3820_config(sis3820, fscanh):
    """Set up SIS3820 based on the fscan1 parameters
    
    Parameters:
        sis3820: SIS3820
            The SIS3820 device
        fscan1: FScan1
            The linear scan record
    """

    total_points = fscanh.number_points.get()
    total_trigger = total_points - 2
    yield from sis3820.set_stop_all(1)
    yield from sis3820.set_num_ch_used(total_trigger)


def xmap_config(xrf, xrf_netcdf, fscanh):
    """Set up XRF and XRF_NetCDF based on parameters in fscanh
    
    Parameters:
        xrf: XRF
            The XRF device
        xrf_netcdf: XRF_NetCDF
            The XRF_NetCDF fileplugin
        fscanh: FScanH
            The fly scan record
    """
    total_points = fscanh.number_points.get()
    total_trigger = total_points - 2
    # yield from xrf_netcdf.st
    yield from xrf.set_pixels_per_run(total_trigger)
    yield from xrf_netcdf.set_pixels_per_run(total_trigger)



"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)


"""

__all__ = """
    fly2d
""".split()

import logging
import numpy as np
import bluesky.preprocessors as bpp
import bluesky.plan_stubs as bps
from mic_common.utils.param_capture import capture_params
from s2idd_uprobe.plans.flyscan_core import _fly2d_scanrecord
from apsbits.core.instrument_init import oregistry

logger = logging.getLogger(__name__)
savedata = oregistry["savedata"]
sample = oregistry["sample"]
mono = oregistry['kohzu_mono']
# scanrecord = oregistry["scanrecord"]
# savedata = scanrecord.savedata

def fly2d_scanrecord(
    samplename: str = "smp1",
    user_comments: str = "",
    width: float = 0,
    x_center: float = None,
    stepsize_x: float = 0,
    height: float = 0,
    y_center: float = None,
    stepsize_y: float = 0,
    dwell_ms: float = 0,
    sample_z: float = None,
    energy_keV: float = None,
    xrf_on: bool = True,
    preamp1_on: bool = False,
):
    """2D Bluesky plan that drives the x- and y- sample motors in fly mode using ScanRecord

    Parameters
    ----------
    samplename:
        The name of the sample for file naming. Default: "smp1". 
    user_comments:
        User comments to be recorded with the scan data. Default is "". 
    width:
        The total width of the scan area in microns. Default: 0. 
    x_center:
        The center position of the scan in the x-direction in microns. If not provided, 
        the current x-motor position will be used as the center. Default: None.
    stepsize_x:
        The step size (spatial resolution) in the x-direction in microns. Default: 0. 
    height:
        The total height of the scan area in microns. Default: 0. 
    y_center:
        The center position of the scan in the y-direction in microns. If not provided, 
        the current y-motor position will be used as the center. Default: None. 
    stepsize_y:
        The step size (spatial resolution) in the y-direction in microns. Default: 0. 
    dwell_ms:
        The dwell time per step in milliseconds. Default: 0. 
    sample_z:
        The sample z position in millimeters. If not provided, the current sample z 
        position will be maintained. Default: None. 
    energy_keV:
        The energy of the incident x-rays in keV. If not provided, the current energy 
        will be used. Default: None. 
    xrf_on:
        Whether to enable the x-ray fluorescence detector. Default is True. 
    preamp1_on:
        Whether to enable preamp1. Preamp1 is used to record metadata. Default is True. 
    """


    
    """Capture the input plan parameters"""
    # Use the current motor positions if not provided
    x_center = round(sample.x.position, 2) if x_center is None else x_center
    y_center = round(sample.y.position, 2) if y_center is None else y_center
    sample_z = round(sample.z.position, 2) if sample_z is None else sample_z
    energy_keV = round(mono.readback.get(), 4) if energy_keV is None else energy_keV

    plan_args = capture_params(fly2d_scanrecord, **locals())
    scan_id = None
    try:
        scan_id = savedata.next_scan_number.get()
    except Exception as e:
        logger.error(f"Error getting scan id: {e}")
        scan_id = None

    md = {"plan_args": plan_args, "scan_id": scan_id}

    @bpp.run_decorator(md=md)
    def _fly2d():
        yield from _fly2d_scanrecord(**plan_args)

    yield from _fly2d()


def fly3d_xanes_scanrecord(
    samplename: str = "smp1",
    user_comments: str = "",
    energy_start: float = None,
    energy_end: float = None,
    energy_step: float = None,
    width: float = 0,
    x_center: float = None,
    stepsize_x: float = 0,
    height: float = 0,
    y_center: float = None,
    stepsize_y: float = 0,
    dwell_ms: float = 0,
    sample_z: float = None,
    xrf_on: bool = True,
    preamp1_on: bool = False,
):

    """ 3D fly scan plan that first go to a desired energy, then drives the x-, y- motors in fly mode using ScanRecord

    Parameters
    ----------
    samplename: str
        The name of the sample for file naming. Default: "smp1". 
    user_comments: str
        User comments to be recorded with the scan data. Default is "". 
    energy_start: float
        The starting energy of the scan in keV. 
    energy_end: float
        The ending energy of the scan in keV. 
    energy_step: float
        The step size (energy resolution) in the x-direction in keV. 
    width: float
        The total width of the scan area in microns. Default: 0. 
    x_center: float
        The center position of the scan in the x-direction in microns. If not provided, 
        the current x-motor position will be used as the center. Default: None. 
    stepsize_x: float
        The step size (spatial resolution) in the x-direction in microns. Default: 0. 
    height: float
        The total height of the scan area in microns. Default: 0. 
    y_center: float
        The center position of the scan in the y-direction in microns. If not provided, 
        the current y-motor position will be used as the center. Default: None. 
    stepsize_y: float
        The step size (spatial resolution) in the y-direction in microns. Default: 0. 
    dwell_ms: float
        The dwell time per step in milliseconds. Default: 0. 
    sample_z: float
        The sample z position in millimeters. If not provided, the current sample z 
        position will be maintained. Default: None. 
    xrf_on: bool
        Whether to enable the x-ray fluorescence detector. Default is True. 
    preamp1_on: bool
        Whether to enable preamp1. Preamp1 is used to record metadata. Default is True. 
    """
    
    """Create the energy array"""
    energy_arr = np.arange(
        energy_start, energy_end + energy_step, energy_step
    )
    logger.info(f"The requested energies are {energy_arr}")

    for i, energy in enumerate(energy_arr):
        logger.info(
            f"Preparing stage to run fly2d scan at {energy} keV, {i+1} of {len(energy_arr)} energies"
        )
        yield from fly2d_scanrecord(
            samplename=samplename,
            user_comments=user_comments,
            width=width,
            x_center=x_center,
            stepsize_x=stepsize_x,
            height=height,
            y_center=y_center,
            stepsize_y=stepsize_y,
            dwell_ms=dwell_ms,
            sample_z=sample_z,
            energy_keV=energy,
            xrf_on=xrf_on,
            preamp1_on=preamp1_on,
        )
        yield from bps.sleep(1)

    


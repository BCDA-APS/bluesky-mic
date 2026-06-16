"""Coarse-to-fine fly2d scan workflow."""

import logging
from pathlib import Path

from apsbits.core.instrument_init import oregistry
from mic_vis.bnp.img_processing import get_coordinate

from .fly2d_scanrecord import fly2d_scanrecord
from bnp.utils.coarse_fine import wait_for_coarse_h5

logger = logging.getLogger(__name__)
savedata = oregistry["savedata"]
sample = oregistry["sample"]
bda = oregistry["bda"]


def coarse_fine_scanrecord(
    samplename: str = "smp1",
    user_comments: str = "",
    width: float = 0,
    x_center: float = None,
    stepsize_x: float = 0,
    height: float = 0,
    y_center: float = None,
    stepsize_y: float = 0,
    dwell_ms: float = 0,
    width_fine: float = 0,
    stepsize_x_fine: float = 0,
    height_fine: float = 0,
    stepsize_y_fine: float = 0,
    dwell_ms_fine: float = 0,
    sample_z: float = None,
    theta: float = None,
    bda_position: float = None,
    elm: str = "",
    mask_elm: str = "",
    use_mask: bool = False,
    n_std: float = 2.0,
    n_cluster: int = 2,
    sel_cluster: int = 1,
    file_wait_timeout: float = 30.0,
    xmap_on: bool = True,
    xp3_on: bool = False,
    eiger_on: bool = False,
    ptycho_exp_factor: float = 1,
):
    """This plan runs a coarse fly2d scan, compute a fine center, then run a fine fly2d scan

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
    width_fine: 
        The total width of the fine scan area in microns. Default: 0. 
    stepsize_x_fine: 
        The step size (spatial resolution) in the x-direction in microns. Default: 0. 
    height_fine: 
        The total height of the fine scan area in microns. Default: 0. 
    stepsize_y_fine: 
        The step size (spatial resolution) in the y-direction in microns. Default: 0. 
    dwell_ms_fine: 
        The dwell time per step in milliseconds. Default: 0. 
    sample_z: 
        The sample z position in millimeters. If not provided, the current sample z 
        position will be maintained. Default: None. 
    theta: 
        The sample theta position in degrees. If not provided, the current sample theta 
        position will be maintained. Default: None. 
    bda_position: 
        The bda position that allows beam to pass. Unit is in millimeters. If not provided, the current bda position 
        will be maintained. Default: None. 
    elm: 
        The element to use for the fine scan center computation. Default: "". 
    mask_elm: 
        This is optional. The element to use for the fine scan center computation. Default: "". 
    use_mask: 
        This is optional. Whether to use the mask for the fine scan center computation. Default: False. 
    n_std: 
        This is optional. The number of standard deviations to use for the fine scan center computation. Default: 2.0. 
    n_cluster: 
        The number of clusters to use for the fine scan center computation. Default: 2. 
    sel_cluster: 
        The cluster to use for the fine scan center computation. Recommended value is n_cluster - 1, which is the cluster with the highest intensity. 
    file_wait_timeout: 
        The timeout for waiting for the coarse scan h5 file. Default: 30.0. 
    xmap_on: 
        Whether to enable the xmap detector. Default: True. 
    xp3_on: 
        Whether to enable the xp3 detector. Default: False. 
    eiger_on: 
        Whether to enable the eiger detector. Default: False. 
    ptycho_exp_factor: 
        The exposure factor for the ptycho detector. Default: 1. 

    """

    if not elm:
        raise ValueError("Parameter 'elm' is required for coarse-fine scans")

    x_center = round(sample.x.piezo.position, 2) if x_center is None else x_center
    y_center = round(sample.y.piezo.position, 2) if y_center is None else y_center
    sample_z = round(sample.z.position, 2) if sample_z is None else sample_z
    theta = round(sample.theta.position, 2) if theta is None else theta
    bda_position = round(bda.x.position, 2) if bda_position is None else bda_position

    coarse_scan_name = str(savedata.next_file_name)
    logger.info("Starting coarse scan for '%s' using output name '%s'", samplename, coarse_scan_name)
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
        theta=theta,
        bda_position=bda_position,
        xmap_on=xmap_on,
        xp3_on=xp3_on,
        eiger_on=eiger_on,
        ptycho_exp_factor=ptycho_exp_factor,
    )

    base_dir = Path(str(savedata.get_auto_storage_path()))
    coarse_h5_path = wait_for_coarse_h5(base_dir, coarse_scan_name, timeout=file_wait_timeout)
    img_proc_dir = base_dir / "img_proc"
    img_proc_dir.mkdir(exist_ok=True)
    figpath = img_proc_dir / f"{coarse_scan_name}_coarse_roi.png"
    fine_x, fine_y = get_coordinate(
        coarse_h5_path,
        elm=elm,
        mask_elm=mask_elm or None,
        use_mask=use_mask,
        n_std=n_std,
        n_cluster=n_cluster,
        sel_cluster=sel_cluster,
        figpath=figpath
    )
    logger.info("Starting fine scan for '%s' at x=%.2f y=%.2f", samplename, fine_x, fine_y)

    yield from fly2d_scanrecord(
        samplename=samplename,
        user_comments=user_comments,
        width=width_fine,
        x_center=fine_x,
        stepsize_x=stepsize_x_fine,
        height=height_fine,
        y_center=fine_y,
        stepsize_y=stepsize_y_fine,
        dwell_ms=dwell_ms_fine,
        sample_z=sample_z,
        theta=theta,
        bda_position=bda_position,
        xmap_on=xmap_on,
        xp3_on=xp3_on,
        eiger_on=eiger_on,
        ptycho_exp_factor=ptycho_exp_factor,
    )

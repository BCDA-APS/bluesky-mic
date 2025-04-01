"""
Creating a bluesky plan that interacts with Scan Record.
This plan is used to test the masterfile generation when using the step1d plan.

@author: yluo(grace227)


"""

__all__ = """
    step1d
""".split()

import logging
import os
import h5py
from pathlib import Path
from apstools.devices import DM_WorkflowConnector
from mic_instrument.devices.data_management import api
from mic_instrument.plans.generallized_scan_1d import generalized_scan_1d
from mic_instrument.plans.workflow_plan import run_workflow
from mic_instrument.plans.dm_plans import dm_submit_workflow_job
from mic_instrument.utils.scan_monitor import execute_scan_1d
from mic_instrument.utils.dm_utils import dm_upload_wait
from mic_instrument.utils.watch_pvs_write_hdf5 import write_scan_master_h5
from mic_instrument.configs.device_config import scan1, samx, savedata, master_file_yaml, netcdf_delimiter
from mic_instrument.plans.helper_funcs import selected_dets, calculate_num_capture, move_to_position
from mic_instrument.configs.device_config import ptychoxrf_dm_args, xrf_dm_args, ptychodus_dm_args


logger = logging.getLogger(__name__)
logger.info(__file__)


def step1d_masterfile_dm(
    samplename="smp1",
    user_comments="",
    width=0,
    x_center=None,
    stepsize_x=0,
    dwell=0,
    smp_theta=None,
    simdet_on=False,
    xrf_me7_on=True,
    ptycho_on=False,
    preamp1_on=False,
    fpga_on=False,
    position_stream=False,
    wf_run=False,
    analysisMachine="mona2",
    ptycho_exp_factor=1,
):
    """1D Bluesky plan that drives the a sample motor in stepping mode using ScanRecord
    
    Parameters
    ----------
    samplename:     
        Str: The name of the sample
    user_comments: 
        Str: The user comments for the scan
    width: 
        Float: The width of the scan
    x_center: 
        Float: The center of the scan
    stepsize_x: 
        Float: The step size of the scan
    dwell: float
        Float: The dwell time of the scan
    smp_theta: 
        Float: The sample theta angle
    simdet_on: 
        Bool: Whether to turn on the simdet
    xrf_me7_on: 
        Bool: Whether to turn on the xrf me7
    ptycho_on: 
        Bool: Whether to turn on the ptycho
    preamp1_on: 
        Bool: Whether to turn on the preamp1
    fpga_on: 
        Bool: Whether to turn on the fpga
    position_stream: 
        Bool: Whether to turn on the position stream
    wf_run: 
        Bool: Whether to run the dm workflow
    analysisMachine: 
        Str: The analysis machine to use
    ptycho_exp_factor:
        Float: The exposure factor for the ptycho. 
    """

    ##TODO Close shutter while setting up scan parameters

    """Set up scan record based on the scan types and parameters"""
    # yield from generalized_scan_1d(scan1, samx, scanmode="LINEAR", **locals())
    yield from generalized_scan_1d(scan1, samx, scanmode="LINEAR", x_center=x_center,
                                   width=width, stepsize_x=stepsize_x, dwell=dwell)

    """Check which detectors to trigger"""
    logger.info("Determining which detectors are selected")
    dets = selected_dets(**locals())

    """Lets config the detectors accordingly"""
    inner_pts = 50  #This is just a placeholder
    savedata.update_next_file_name()
    filename = savedata.next_file_name.replace(".mda", "")
    xrf_me7_hdf = None
    ptycho_hdf = None

    for det_name, det_var in dets.items():
        cam = det_var['cam']
        file_plugin = det_var['file_plugin']

        if det_name == "xrf_me7":
            if cam is not None: 
                yield from cam.scan_init(exposure_time=dwell, num_images=inner_pts)
        
            if file_plugin is not None:
                yield from file_plugin.setup_file_writer(
                    savedata,
                    det_name,
                    inner_pts,
                    filename=filename,
                    beamline_delimiter=netcdf_delimiter,
                )
                xrf_me7_hdf = file_plugin

        elif det_name == "ptycho":
            if cam is not None:
                yield from cam.scan_init(exposure_time=dwell, num_images=inner_pts, 
                                         ptycho_exp_factor=ptycho_exp_factor)
            if file_plugin is not None:
                #If an hdf5 file plugin is used, we need to disable the Eiger's default file writer.
                yield from cam.set_file_writer_enable("Disable")

                yield from file_plugin.setup_file_writer(
                    savedata,
                    det_name,
                    inner_pts,
                    filename=filename,
                    beamline_delimiter=netcdf_delimiter,
                )
                ptycho_hdf = file_plugin
    
    """Generate master file"""
    next_file_name = savedata.next_file_name.replace(".mda", "_master.h5")
    scan_master_h5_path = Path(savedata.file_system.value) / next_file_name
    write_scan_master_h5(master_file_yaml, scan_master_h5_path)
    logger.info(f"Scan master file saved to {scan_master_h5_path}")

    """Start executing scan"""
    yield from execute_scan_1d(scan1, scan_name=savedata.next_file_name)

    """Generate detector master file and update detector h5 master file in the scan master file"""
    det_h5_master_path = {}
    logger.info(f"Generating detector master file and updating detector h5 master file in the scan master file")
    for det_name, det_var in dets.items():
        cam = det_var['cam']
        file_plugin = det_var['file_plugin']
        cap_det_name = det_name.upper()
        if all([cam is not None, file_plugin is not None]): 
            det_dir = file_plugin.file_path.value
            master_h5_path = Path(det_dir) / next_file_name.replace("_master.h5", ".h5")
            try:
                cam.write_h5(master_h5_path, det_dir, filename, cap_det_name)
                det_h5_master_path[cap_det_name] = master_h5_path
            except Exception as e:
                logger.error(f"Error writing HDF5 file for {cap_det_name}: {e}")

    with h5py.File(scan_master_h5_path, 'r+') as f:
        group = f.create_group("detectors")
        for det_name, master_h5_path in det_h5_master_path.items():
            rel_path = os.path.relpath(Path(master_h5_path), Path(scan_master_h5_path).parent)
            group[det_name] = h5py.ExternalLink(rel_path, det_name)

    logger.info(f"Detector master file and detector h5 master file in the scan master file have been updated")
    

    #############################
    # START THE APS DM WORKFLOW #
    #############################

    if wf_run:
        dm_workflow = DM_WorkflowConnector(name=samplename, labels=("dm",))

        if all([xrf_me7_on, ptycho_on]):
            WORKFLOW = "ptycho-xrf"
            argsDict = ptychoxrf_dm_args.copy()
            argsDict['experimentName'] = 'blueskydev'
            argsDict['dataDir'] = 'XRF_ME7/'
            argsDict['ptychoDetectorName'] = 'PTYCHO'
            argsDict['ptychoFilePath'] = '19ide_bluesky_0029.h5'
            argsDict['filePath'] = '19ide_bluesky_0029_0.hdf5'
            # argsDict['ptychoFilePath'] = ptycho_hdf.file_path.get() #'/gdata/dm/19ID/2025-1/blueskydev/data/PTYCHO/'
            # argsDict['ptychoFilePath'] = 'data/PTYCHO/_.hdf5'
            # argsDict['filePath'] = xrf_me7_hdf.file_name.get() + '.hdf5' # '19ide_bluesky_0020'
        elif xrf_me7_on:
            WORKFLOW = "xrf-maps"
            argsDict = xrf_dm_args.copy()
            argsDict['experimentName'] = 'blueskydev'
            argsDict['dataDir'] = 'XRF_ME7/'
        # else:
        #     WORKFLOW = "ptychodus"
        #     argsDict = ptychodus_dm_args.copy()

        ##TODO Modify argsDict accordingly based on the scan parameters
        argsDict['analysisMachine'] = analysisMachine

        yield from dm_submit_workflow_job(WORKFLOW, argsDict)
        logger.info(f"{len(api.listProcessingJobs())=!r}")
        logger.info("DM workflow Finished!")

    logger.info("end of plan")

# else:
#     logger.info(f"Having issue connecting to scan record: {scan1.prefix}")

    # yield from bps.sleep(1)
    # print("end of plan")


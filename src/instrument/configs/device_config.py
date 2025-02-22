"""Create scanrecords that are specific to 2idd-microprobe

Created on Jan 14 2025

@author: yluo (grace227)
"""

import pathlib
from mic_instrument.devices.scan_record import ScanRecord
from mic_instrument.devices.save_data import SaveDataMic
from mic_instrument.devices.ad_fileplugin import DetHDF5, DetNetCDF
from mic_instrument.devices.xmap import XMAP
from mic_instrument.devices.eiger500k import Eiger500k
from mic_instrument.devices.sis3820 import SIS3820
from mic_instrument.utils.config_loaders import iconfig
from mic_instrument.utils.config_loaders import load_config_yaml
from ophyd import EpicsSignal
from ophyd import EpicsMotor

# from mic_instrument.devices.simdet import SimDet, SimDetHDF5

scan1 = ScanRecord(iconfig.get("DEVICES")["SCAN1"], name="scan1")
scan2 = ScanRecord(iconfig.get("DEVICES")["SCAN2"], name="scan2")
stepdwell = EpicsSignal(iconfig.get("USERCALC")["STEPSCAN_DWELL"], name="stepdwell")
fscan1 = ScanRecord(iconfig.get("DEVICES")["FSCAN1"], name="fscan1")
fscanh = ScanRecord(iconfig.get("DEVICES")["FSCANH"], name="fscanh")
fscanh_samx = EpicsSignal(
    iconfig.get("USERCALC")["FSCANH_POSITIONER"], name="fscanh_samx"
)
fscanh_dwell = EpicsSignal(iconfig.get("USERCALC")["FSCANH_DWELL"], name="fscanh_dwell")
samx = EpicsMotor(iconfig.get("POSITIONERS")["X_MOTOR"], name="samx")
samy = EpicsMotor(iconfig.get("POSITIONERS")["Y_MOTOR"], name="samy")
samz = EpicsMotor(iconfig.get("POSITIONERS")["Z_MOTOR"], name="samz")
samtheta = EpicsMotor(iconfig.get("POSITIONERS")["THETA_MOTOR"], name="samtheta")
savedata = SaveDataMic(iconfig.get("DEVICES")["SAVE_DATA"], name="savedata")
hydra1_startposition = EpicsSignal(
    iconfig.get("OTHER_SIGNALS")["HYDRA1_STARTPOSITION"], name="hydra1_startposition"
)
scan_overhead = iconfig.get("POSITIONERS")["SCAN_OVERHEAD"]

netcdf_delimiter = iconfig.get("DETECTOR")["FILE_DELIMITER"]
xrf = XMAP(
    iconfig.get("DETECTOR")["XMAP_4Chan"]["PV_PREFIX"],
    name=iconfig.get("DETECTOR")["XMAP_4Chan"]["NAME"],
)
xmap_buffer = iconfig.get("DETECTOR")["XMAP_4Chan"]["BUFFER"]

xrf_netcdf = DetNetCDF(
    iconfig.get("DETECTOR")["XMAP_4Chan"]["NETCDF_PV_PREFIX"],
    name=iconfig.get("DETECTOR")["XMAP_4Chan"]["NAME"] + "_netcdf",
)

sis3820 = SIS3820(
    iconfig.get("DETECTOR")["SIS3820"]["PV_PREFIX"],
    name=iconfig.get("DETECTOR")["SIS3820"]["NAME"],
)

eiger = Eiger500k(
    iconfig.get("DETECTOR")["AD_EIGER_PTYCHO"]["PV_PREFIX"],
    name=iconfig.get("DETECTOR")["AD_EIGER_PTYCHO"]["NAME"],
)

if iconfig.get("DETECTOR")["AD_EIGER_PTYCHO"]["HDF5_PV_PREFIX"] is not "":
    eiger_hdf5 = DetHDF5(
        iconfig.get("DETECTOR")["AD_EIGER_PTYCHO"]["HDF5_PV_PREFIX"],
        name=iconfig.get("DETECTOR")["AD_EIGER_PTYCHO"]["NAME"] + "_hdf",
    )
else:
    eiger_hdf5 = None

# Create detector name mapping
det_name_mapping = {
    "xrf": {"cam": xrf, "file_plugin": xrf_netcdf},
    "preamp": {"cam": None, "file_plugin": None},
    "fpga": {"cam": None, "file_plugin": None},
    "ptycho": {"cam": eiger, "file_plugin": eiger_hdf5},
    "struck": {"cam": sis3820, "file_plugin": None},
}


## DM workflow config ##
instrument_path = pathlib.Path(__file__).parent.parent
xrf_workflow_yaml_path = instrument_path / "configs" / "xrf_workflow.yml"
ptychoxrf_workflow_yaml_path = instrument_path / "configs" / "ptycho_xrf_workflow.yml"
ptychodus_workflow_yaml_path = instrument_path / "configs" / "ptychodus_workflow.yml"
xrf_dm_args = load_config_yaml(xrf_workflow_yaml_path)
ptychoxrf_dm_args = load_config_yaml(ptychoxrf_workflow_yaml_path)
ptychodus_dm_args = load_config_yaml(ptychodus_workflow_yaml_path)

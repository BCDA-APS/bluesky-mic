"""Create scanrecords that are specific to 19id-ISN

Created on Dec 04 2024

@author: yluo (grace227)
"""

import pathlib

from apsbits.utils.config_loaders import iconfig
from apsbits.utils.config_loaders import load_config_yaml
from ophyd import EpicsMotor

from mic_instrument.devices.ad_fileplugin import DetHDF5
from mic_instrument.devices.ad_fileplugin import DetNetCDF  # noqa: F401
from mic_instrument.devices.eiger1m import Eiger1M
from mic_instrument.devices.save_data import SaveDataMic
from mic_instrument.devices.scan_record import ScanRecord
from mic_instrument.devices.tetramm import TetraMM
from mic_instrument.devices.xspress3 import Xspress3

# from mic_instrument.devices.simdet import SimDet, SimDetHDF5

# XRF detector configuration
xmap_buffer = 1000  # Default buffer size for XRF detector

scan1 = ScanRecord(iconfig.get("DEVICES")["SCAN1"], name="scan1")
scan2 = ScanRecord(iconfig.get("DEVICES")["SCAN2"], name="scan2")
samx = EpicsMotor(iconfig.get("POSITIONERS")["X_MOTOR"], name="samx")
samy = EpicsMotor(iconfig.get("POSITIONERS")["Y_MOTOR"], name="samy")
samz = EpicsMotor(iconfig.get("POSITIONERS")["Z_MOTOR"], name="samz")
samr = EpicsMotor(iconfig.get("POSITIONERS")["R_MOTOR"], name="samr")
scan_overhead = iconfig.get("POSITIONERS")["SCAN_OVERHEAD"]
savedata = SaveDataMic(iconfig.get("DEVICES")["SAVE_DATA"], name="savedata")
local_mountpath = iconfig.get("STORAGE")["PATH"]


xrf_me7 = Xspress3(
    iconfig.get("AREA_DETECTOR")["AD_XSP3_8Chan"]["PV_PREFIX"],
    name=iconfig.get("AREA_DETECTOR")["AD_XSP3_8Chan"]["NAME"],
)
xrf_me7_hdf = DetHDF5(
    iconfig.get("AREA_DETECTOR")["AD_XSP3_8Chan"]["HDF5_PV_PREFIX"],
    name=iconfig.get("AREA_DETECTOR")["AD_XSP3_8Chan"]["NAME"] + "_hdf",
)

ptycho = Eiger1M(
    iconfig.get("AREA_DETECTOR")["AD_EIGER_PTYCHO"]["PV_PREFIX"],
    name=iconfig.get("AREA_DETECTOR")["AD_EIGER_PTYCHO"]["NAME"],
)
ptycho_hdf = DetHDF5(
    iconfig.get("AREA_DETECTOR")["AD_EIGER_PTYCHO"]["HDF5_PV_PREFIX"],
    name=iconfig.get("AREA_DETECTOR")["AD_EIGER_PTYCHO"]["NAME"] + "_hdf",
)

tetramm1 = TetraMM(
    iconfig.get("AREA_DETECTOR")["TETRAMM1"]["PV_PREFIX"],
    name=iconfig.get("AREA_DETECTOR")["TETRAMM1"]["NAME"],
)
tetramm1_netcdf = None
# tetramm1_netcdf = DetNetCDF(
#     iconfig.get("DETECTOR")["TETRAMM1"]["NETCDF_PV_PREFIX"],
#     name=iconfig.get("DETECTOR")["TETRAMM1"]["NAME"] + "_netcdf",
# )

netcdf_delimiter = iconfig.get("FILE_DELIMITER")
xrf_me7_hdf.micdata_mountpath = local_mountpath
# tetramm1_netcdf.micdata_mountpath = local_mountpath


# Create detector name mapping
det_name_mapping = {
    "xrf_me7": {"cam": xrf_me7, "file_plugin": xrf_me7_hdf},
    "preamp1": {"cam": tetramm1, "file_plugin": tetramm1_netcdf},
    # "preamp2": {"cam": tetramm2, "file_plugin": tetramm2_netcdf},
    "fpga": {"cam": None, "file_plugin": None},
    "ptycho": {"cam": ptycho, "file_plugin": ptycho_hdf},
}

## Scan master file config ##
instrument_path = pathlib.Path(__file__).parent.parent
master_file_config_path = instrument_path / "configs" / "masterFileConfig.yml"
master_file_yaml = load_config_yaml(master_file_config_path)


## DM workflow config ##
xrf_workflow_yaml_path = instrument_path / "configs" / "xrf_workflow.yml"
ptychoxrf_workflow_yaml_path = instrument_path / "configs" / "ptycho_xrf_workflow.yml"
ptychodus_workflow_yaml_path = instrument_path / "configs" / "ptychodus_workflow.yml"
xrf_dm_args = load_config_yaml(xrf_workflow_yaml_path)
ptychoxrf_dm_args = load_config_yaml(ptychoxrf_workflow_yaml_path)
ptychodus_dm_args = load_config_yaml(ptychodus_workflow_yaml_path)

"""Create scanrecords that are specific to 2idd-microprobe

Created on Jan 14 2025

@author: yluo (grace227)
"""

import pathlib

from mic_instrument.devices.kohzu import KohzuMono
from mic_instrument.devices.save_data import SaveDataMic
from mic_instrument.devices.xmap import XMAP
from mic_instrument.utils.config_loaders import iconfig
from mic_instrument.utils.config_loaders import load_config_yaml

scan_overhead = iconfig.get("POSITIONERS")["SCAN_OVERHEAD"]
savedata = SaveDataMic(iconfig.get("DEVICES")["SAVE_DATA"], name="savedata")
micdata_mountpath = iconfig.get("STORAGE")["PATH"]

xrf = XMAP(
    iconfig.get("DETECTOR")["XMAP_1Chan"]["PV_PREFIX"],
    name=iconfig.get("DETECTOR")["XMAP_1Chan"]["NAME"],
)
xmap_buffer = iconfig.get("DETECTOR")["XMAP_1Chan"]["BUFFER"]

# xrf_netcdf = DetNetCDF(
#     iconfig.get("DETECTOR")["XMAP_1Chan"]["NETCDF_PV_PREFIX"],
#     name=iconfig.get("DETECTOR")["XMAP_1Chan"]["NAME"] + "_netcdf",
# )

# tetramm1 = TetraMM(
#     iconfig.get("DETECTOR")["TETRAMM1"]["PV_PREFIX"],
#     name=iconfig.get("DETECTOR")["TETRAMM1"]["NAME"],
# )
# tetramm1_netcdf = DetNetCDF(
#     iconfig.get("DETECTOR")["TETRAMM1"]["NETCDF_PV_PREFIX"],
#     name=iconfig.get("DETECTOR")["TETRAMM1"]["NAME"] + "_netcdf",
# )

# tetramm2 = TetraMM(
#     iconfig.get("DETECTOR")["TETRAMM2"]["PV_PREFIX"],
#     name=iconfig.get("DETECTOR")["TETRAMM2"]["NAME"],
# )
# tetramm2_netcdf = DetNetCDF(
#     iconfig.get("DETECTOR")["TETRAMM2"]["NETCDF_PV_PREFIX"],
#     name=iconfig.get("DETECTOR")["TETRAMM2"]["NAME"] + "_netcdf",
# )

netcdf_delimiter = iconfig.get("DETECTOR")["FILE_DELIMITER"]
xrf_netcdf.micdata_mountpath = micdata_mountpath
tetramm1_netcdf.micdata_mountpath = micdata_mountpath
tetramm2_netcdf.micdata_mountpath = micdata_mountpath

# sis3820 = SIS3820(
#     iconfig.get("DETECTOR")["SIS3820"]["PV_PREFIX"],
#     name=iconfig.get("DETECTOR")["SIS3820"]["NAME"],
# )

kohzu = KohzuMono(
    iconfig.get("KOHZU_MONO")["PV_PREFIX"], name=iconfig.get("KOHZU_MONO")["NAME"]
)

# Create detector name mapping
det_name_mapping = {
    "xrf": {"cam": xrf, "file_plugin": xrf_netcdf},
    "preamp1": {"cam": tetramm1, "file_plugin": tetramm1_netcdf},
    "preamp2": {"cam": tetramm2, "file_plugin": tetramm2_netcdf},
    "fpga": {"cam": None, "file_plugin": None},
    "ptycho": {"cam": None, "file_plugin": None},
    "struck": {"cam": sis3820, "file_plugin": None},
}


# xrf_me7_hdf = DetHDF5(
#     iconfig.get("AREA_DETECTOR")["AD_XSP3_8Chan"]["HDF5_PV_PREFIX"],
#     name=iconfig.get("AREA_DETECTOR")["AD_XSP3_8Chan"]["NAME"] + "_hdf",
# )

# simdet = SimDet(iconfig.get("DEVICES")["SIMDET_CAM"], name="simdet")
# simdeth5file = SimDetHDF5(iconfig.get("DEVICES")["SIMDET_HDF5"], name="simdet_hdf5")

## DM workflow config ##
instrument_path = pathlib.Path(__file__).parent.parent
xrf_workflow_yaml_path = instrument_path / "configs" / "xrf_workflow.yml"
ptychoxrf_workflow_yaml_path = instrument_path / "configs" / "ptycho_xrf_workflow.yml"
ptychodus_workflow_yaml_path = instrument_path / "configs" / "ptychodus_workflow.yml"
xrf_dm_args = load_config_yaml(xrf_workflow_yaml_path)
ptychoxrf_dm_args = load_config_yaml(ptychoxrf_workflow_yaml_path)
ptychodus_dm_args = load_config_yaml(ptychodus_workflow_yaml_path)

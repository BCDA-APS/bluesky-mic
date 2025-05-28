"""Create scanrecords that are specific to 19id-ISN

Created on Dec 04 2024

@author: yluo (grace227)
"""

import pathlib

from apsbits.utils.config_loaders import load_config_yaml

# from mic_instrument.devices.simdet import SimDet, SimDetHDF5


# Create detector name mapping
# det_name_mapping = {
#     "xrf_me7": {"cam": xrf_me7, "file_plugin": xrf_me7_hdf},
#     "preamp1": {"cam": tetramm1, "file_plugin": tetramm1_netcdf},
#     # "preamp2": {"cam": tetramm2, "file_plugin": tetramm2_netcdf},
#     "fpga": {"cam": None, "file_plugin": None},
#     "ptycho": {"cam": ptycho, "file_plugin": ptycho_hdf},
# }

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

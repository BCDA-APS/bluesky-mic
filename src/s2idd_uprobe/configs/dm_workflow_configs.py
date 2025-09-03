"""Create scanrecords that are specific to 2idd-microprobe

Created on Jan 14 2025

@author: yluo (grace227)
"""

from pathlib import Path

from apsbits.utils.config_loaders import load_config_yaml

instrument_path = Path(__file__).parent

## DM workflow config ##
xrf_workflow_yaml_path = instrument_path / "configs" / "xrf_workflow.yml"
ptychoxrf_workflow_yaml_path = instrument_path / "configs" / "ptycho_xrf_workflow.yml"
ptychodus_workflow_yaml_path = instrument_path / "configs" / "ptychodus_workflow.yml"
xrf_dm_args = load_config_yaml(xrf_workflow_yaml_path)
ptychoxrf_dm_args = load_config_yaml(ptychoxrf_workflow_yaml_path)
ptychodus_dm_args = load_config_yaml(ptychodus_workflow_yaml_path)


# # Create detector name mapping
# det_name_mapping = {
#     "xrf": {"cam": xrf, "file_plugin": xrf_netcdf},
#     "preamp1": {"cam": tetramm1, "file_plugin": tetramm1_netcdf},
#     "preamp2": {"cam": tetramm2, "file_plugin": tetramm2_netcdf},
#     "fpga": {"cam": None, "file_plugin": None},
#     "ptycho": {"cam": None, "file_plugin": None},
#     "struck": {"cam": sis3820, "file_plugin": None},
# }

""" Create scanrecords that are specific to 2idd-microprobe

Created on Jan 14 2025

@author: yluo (grace227)
"""

from mic_instrument.devices.scan_record import ScanRecord
from ophyd import EpicsSignal
from mic_instrument.devices.save_data import SaveDataMic
from mic_instrument.devices.area_det_hdf import DetHDF5
from ophyd import EpicsMotor
from mic_instrument.utils.config_loaders import iconfig
from mic_instrument.utils.config_loaders import load_config_yaml
import pathlib

# from mic_instrument.devices.simdet import SimDet, SimDetHDF5
from mic_instrument.devices.xspress3 import Xspress3

# from ophyd.areadetector.cam import Xspress3DetectorCam

scan1 = ScanRecord(iconfig.get("DEVICES")["SCAN1"], name="scan1")
scan2 = ScanRecord(iconfig.get("DEVICES")["SCAN2"], name="scan2")
fscan1 = ScanRecord(iconfig.get("DEVICES")["FSCAN1"], name="fscan1")
fscanh = ScanRecord(iconfig.get("DEVICES")["FSCANH"], name="fscanh")
fscanh_samx = EpicsSignal(iconfig.get("USERCALC")["FSCANH_POSITIONER"], name="fscanh_samx")
samx = EpicsMotor(iconfig.get("POSITIONERS")["X_MOTOR"], name="samx")
samy = EpicsMotor(iconfig.get("POSITIONERS")["Y_MOTOR"], name="samy")
samz = EpicsMotor(iconfig.get("POSITIONERS")["Z_MOTOR"], name="samz")
savedata = SaveDataMic(iconfig.get("DEVICES")["SAVE_DATA"], name="savedata")

xrf_me7 = Xspress3(
    iconfig.get("AREA_DETECTOR")["AD_XSP3_8Chan"]["PV_PREFIX"],
    name=iconfig.get("AREA_DETECTOR")["AD_XSP3_8Chan"]["NAME"],
)
xrf_me7_hdf = DetHDF5(
    iconfig.get("AREA_DETECTOR")["AD_XSP3_8Chan"]["HDF5_PV_PREFIX"],
    name=iconfig.get("AREA_DETECTOR")["AD_XSP3_8Chan"]["NAME"] + "_hdf",
)

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

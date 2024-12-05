""" Create scanrecords that are specific to 19id-ISN

Created on Dec 04 2024

@author: yluo (grace227)
"""

from mic_instrument.devices.scan_record import ScanRecord
from mic_instrument.devices.save_data import SaveDataMic
from mic_instrument.devices.area_det_hdf import DetHDF5
from mic_instrument.utils.config_loaders import iconfig

# from mic_instrument.devices.simdet import SimDet, SimDetHDF5
from mic_instrument.devices.xspress3 import Xspress3
# from ophyd.areadetector.cam import Xspress3DetectorCam

scan1 = ScanRecord(iconfig.get("DEVICES")["SCAN1"], name="scan1")
scan2 = ScanRecord(iconfig.get("DEVICES")["SCAN2"], name="scan2")
savedata = SaveDataMic(iconfig.get("DEVICES")["SAVE_DATA"], name="savedata")
xrf_me7 = Xspress3(
    iconfig.get("AREA_DETECTOR")["AD_XSP3_8Chan"]["PV_PREFIX"],
    name=iconfig.get("AREA_DETECTOR")["AD_XSP3_8Chan"]["NAME"],
)
xrf_me7_hdf = DetHDF5(
    iconfig.get("AREA_DETECTOR")["AD_XSP3_8Chan"]["HDF5_PV_PREFIX"],
    name=iconfig.get("AREA_DETECTOR")["AD_XSP3_8Chan"]["NAME"]+"_hdf",
)

# simdet = SimDet(iconfig.get("DEVICES")["SIMDET_CAM"], name="simdet")
# simdeth5file = SimDetHDF5(iconfig.get("DEVICES")["SIMDET_HDF5"], name="simdet_hdf5")

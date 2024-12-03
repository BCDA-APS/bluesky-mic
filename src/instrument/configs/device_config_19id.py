""" Create scanrecords that are specific to 19id-ISN"""

from mic_instrument.devices.scan_record import ScanRecord
from mic_instrument.utils.config_loaders import iconfig

# from mic_instrument.devices.simdet import SimDet, SimDetHDF5
from mic_instrument.devices.xspress3 import Xspress3

scan1 = ScanRecord(iconfig.get("DEVICES")["SCAN1"], name="scan1")
scan2 = ScanRecord(iconfig.get("DEVICES")["SCAN2"], name="scan2")
xrf_me7 = Xspress3(
    iconfig.get("AREA_DETECTOR")["AD_XSP3_8Chan"]["PV_PREFIX"],
    name=iconfig.get("AREA_DETECTOR")["AD_XSP3_8Chan"]["NAME"],
)

# simdet = SimDet(iconfig.get("DEVICES")["SIMDET_CAM"], name="simdet")
# simdeth5file = SimDetHDF5(iconfig.get("DEVICES")["SIMDET_HDF5"], name="simdet_hdf5")

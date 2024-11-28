""" Create scanrecords that are specific to 2IDD"""

from mic_instrument.devices.scan_record import ScanRecord
from mic_instrument.utils.config_loaders import iconfig
from mic_instrument.devices.simdet import SimDet, SimDetHDF5

scan1 = ScanRecord(iconfig.get("DEVICES")["SCAN1"], name="scan1")
scan2 = ScanRecord(iconfig.get("DEVICES")["SCAN2"], name="scan2")
simdet = SimDet(iconfig.get("DEVICES")["SIMDET_CAM"], name="simdet")
simdeth5file = SimDetHDF5(iconfig.get("DEVICES")["SIMDET_HDF5"], name="simdet_hdf5")

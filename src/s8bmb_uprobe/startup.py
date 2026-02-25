"""
Start Bluesky Data Acquisition sessions of all kinds.

Includes:

* Python script
* IPython console
* Jupyter notebook
* Bluesky queueserver
"""

# Standard Library Imports
import logging
from pathlib import Path

# Core Functions
from apsbits.core.best_effort_init import init_bec_peaks
from apsbits.core.catalog_init import init_catalog
from apsbits.core.instrument_init import init_instrument
from apsbits.core.instrument_init import make_devices
from apsbits.core.run_engine_init import init_RE

# Utility functions
from apstools.utils.aps_data_management import dm_setup
from apsbits.utils.aps_functions import host_on_aps_subnet

# Configuration functions
from apsbits.utils.config_loaders import load_config
from apsbits.utils.helper_functions import register_bluesky_magics
from apsbits.utils.helper_functions import running_in_queueserver
from apsbits.utils.logging_setup import configure_logging

# Utility functions from apstools and bluesky
from apstools.utils import listobjects, listplans
from bluesky import plan_stubs as bps
from bluesky import plans as bp

# Other functions
import time

# Configuration block
# Get the path to the instrument package
# Load configuration to be used by the instrument.
instrument_path = Path(__file__).parent
iconfig_path = instrument_path / "configs" / "iconfig.yml"
iconfig = load_config(iconfig_path)

# Additional logging configuration
# only needed if using different logging setup
# from the one in the apsbits package
extra_logging_configs_path = instrument_path / "configs" / "extra_logging.yml"
configure_logging(extra_logging_configs_path=extra_logging_configs_path)

logger = logging.getLogger(__name__)
logger.info("Starting Instrument with iconfig: %s", iconfig_path)

# initialize instrument
instrument, oregistry = init_instrument("guarneri")

# Discard oregistry items loaded above.
oregistry.clear()

# Configure the session with callbacks, devices, and plans.
#dm_setup(iconfig.get("DM_SETUP_FILE"))

# Command-line tools, such as %wa, %ct, ...
register_bluesky_magics()

# Bluesky initialization block
bec, peaks = init_bec_peaks(iconfig)
cat = init_catalog(iconfig)
RE, sd = init_RE(iconfig, subscribers=[bec, cat])

# Experiment specific logic, device and plan loading. # Create the devices.
make_devices(clear=False, file="devices.yml", device_manager=instrument)
time.sleep(1)

try:
    sd = oregistry["savedata"]
    sd.micdata_mountpath = iconfig.get("SAVE_DATA")["MOUNT_PATH"]
    sd.storage_path = iconfig.get("STORAGE")["MICDATA_MOUNTPATH"]
except KeyError:
    logger.info("savedata not found, skipping")

try:
   xp3 = oregistry["xp3"]
   xp3.fileplugin.savedata = oregistry["savedata"]
   xp3.fileplugin.micdata_mountpath = iconfig.get("XSPRESS3")["MOUNT_PATH"]
   xp3.fileplugin.delimiter = iconfig.get("STORAGE")["FILE_DELIMITER"]
   xp3.fileplugin.det_foldername = iconfig.get("XSPRESS3")["DET_FOLDERNAME"]

except KeyError:
   logger.info("xp3 not found or xp3.fileplugin not connected or scanrecord not found, skipping")


# Optional Nexus callback block
if iconfig.get("NEXUS_DATA_FILES", {}).get("ENABLE", False):
    from mic_common.callbacks.nexus_data_file_writer import nxwriter_init

    nxwriter = nxwriter_init(RE)
    try:
        nxwriter.savedata = oregistry["savedata"]
        nxwriter.micdata_mountpath = iconfig.get("STORAGE")["MICDATA_MOUNTPATH"]
    except KeyError:
        logger.info("savedata not found, skipping")




# # from .plans import *
# from .plans.test_nexus import test_nexus
#from .plans.fly1d import fly1d
#from .plans.fly2d import fly2d
from .plans.fly2d_scanrecord import fly2d_scanrecord
from .plans.step2d_scanrecord import step2d_scanrecord
# #from .plans.step2d import step2d
# # from .plans.step1d import step1d



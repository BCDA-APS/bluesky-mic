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
dm_setup(iconfig.get("DM_SETUP_FILE"))

# Command-line tools, such as %wa, %ct, ...
register_bluesky_magics()

# Bluesky initialization block
bec, peaks = init_bec_peaks(iconfig)
cat = init_catalog(iconfig)
RE, sd = init_RE(iconfig, subscribers=[bec, cat])

# Experiment specific logic, device and plan loading. # Create the devices.
make_devices(clear=False, file="devices.yml", device_manager=instrument)

try:
    xrf = oregistry["xrf"]
    xrf.cam.buffer_size = iconfig.get("XMAP")["BUFFER"]
    xrf.fileplugin.micdata_mountpath = iconfig.get("XMAP")["MOUNT_PATH"]
    xrf.fileplugin.delimiter = iconfig.get("STORAGE")["FILE_DELIMITER"]
    xrf.fileplugin.det_foldername = iconfig.get("XMAP")["DET_FOLDERNAME"]
    # xrf.fileplugin.savedata = oregistry["scanrecord"].savedata
    xrf.fileplugin.savedata = oregistry["savedata"]
except KeyError:
    logger.info("xrf not found or xrf.fileplugin not connected or scanrecord not found, skipping")

try:
    tmm1 = oregistry["tmm1"]
    tmm1.fileplugin.micdata_mountpath = iconfig.get("STORAGE")["MICDATA_MOUNTPATH"]
    tmm1.fileplugin.delimiter = iconfig.get("STORAGE")["FILE_DELIMITER"]
    tmm1.fileplugin.det_foldername = iconfig.get("TETRAMM")["DET_FOLDERNAME"]
    # tmm1.fileplugin.savedata = oregistry["scanrecord"].savedata
    tmm1.fileplugin.savedata = oregistry["savedata"]
except KeyError:
    logger.info("tmm1 not found or tmm1.fileplugin not connected or scanrecord not found, skipping")

# Optional Nexus callback block
if iconfig.get("NEXUS_DATA_FILES", {}).get("ENABLE", False):
    from mic_common.callbacks.nexus_data_file_writer import nxwriter_init

    nxwriter = nxwriter_init(RE)
    try:
        # nxwriter.savedata = oregistry["scanrecord"].savedata
        nxwriter.savedata = oregistry["savedata"]
        nxwriter.micdata_mountpath = iconfig.get("STORAGE")["MICDATA_MOUNTPATH"]
    except KeyError:
        logger.info("savedata not found, skipping")




# # from .plans import *
# from .plans.test_nexus import test_nexus
from .plans.fly1d import fly1d
from .plans.fly2d import fly2d
from .plans.fly2d_scanrecord import fly2d_scanrecord
from .plans.step1d_scanrecord import step1d_scanrecord
# # from .plans.step2d import step2d
# # from .plans.step1d import step1d



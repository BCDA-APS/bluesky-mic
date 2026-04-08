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
from mic_common.utils.beamline_monitor_manifest import generate_beamline_monitor_manifest

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
    savedata = oregistry["savedata"]
    savedata.micdata_mountpath = iconfig.get("SAVE_DATA")["MOUNT_PATH"]
    savedata.storage_path = iconfig.get("STORAGE")["MICDATA_MOUNTPATH"]
    savedata.auto_mountpath = iconfig.get("STORAGE")["AUTO_MOUNTPATH"]
except KeyError:
    logger.info("savedata not found, skipping")

try:
    xmap = oregistry["xmap"]
    xmap.cam.buffer_size = iconfig.get("XMAP")["BUFFER"]
    xmap.fileplugin.micdata_mountpath = iconfig.get("XMAP")["MOUNT_PATH"]
    xmap.fileplugin.delimiter = iconfig.get("STORAGE")["FILE_DELIMITER"]
    xmap.fileplugin.det_foldername = iconfig.get("XMAP")["DET_FOLDERNAME"]
    xmap.fileplugin.savedata = oregistry["savedata"]
except KeyError:
    logger.info("xmap not found or xmap.fileplugin not connected or scanrecord not found, skipping")

try:
    eiger = oregistry["eiger"]
    eiger.fileplugin.micdata_mountpath = iconfig.get("EIGER")["MOUNT_PATH"]
    eiger.fileplugin.delimiter = iconfig.get("STORAGE")["FILE_DELIMITER"]
    eiger.fileplugin.det_foldername = iconfig.get("EIGER")["DET_FOLDERNAME"]
    eiger.fileplugin.savedata = oregistry["savedata"]
except KeyError:
    logger.info("eiger not found or eiger.fileplugin not connected or scanrecord not found, skipping")

try:
    xp3 = oregistry["xp3"]
    xp3.fileplugin.micdata_mountpath = iconfig.get("XP3")["MOUNT_PATH"]
    xp3.fileplugin.delimiter = iconfig.get("STORAGE")["FILE_DELIMITER"]
    xp3.fileplugin.det_foldername = iconfig.get("XP3")["DET_FOLDERNAME"]
    xp3.fileplugin.savedata = oregistry["savedata"]
except KeyError:
    logger.info("xp3 not found or xp3.fileplugin not connected or scanrecord not found, skipping")



# Optional Nexus callback block
if iconfig.get("NEXUS_DATA_FILES", {}).get("ENABLE", False):
    from mic_common.callbacks.nexus_data_file_writer import nxwriter_init

    nxwriter = nxwriter_init(RE)
    nxwriter.name = "nxwriter"
    oregistry.register(nxwriter, labels=["nxwriter"])
    logger.info("Adding nxwriter to oregistry")
    try:
        # nxwriter.savedata = oregistry["scanrecord"].savedata
        nxwriter.savedata = oregistry["savedata"]
        nxwriter.micdata_mountpath = iconfig.get("STORAGE")["MICDATA_MOUNTPATH"]
    except KeyError:
        logger.info("savedata not found, skipping")


# # # from .plans import *
# # from .plans.test_nexus import test_nexus
# # #from .plans.fly2d import fly2d
from .plans.fly2d_scanrecord import fly2d_scanrecord
from .plans.coarse_fine_scanrecord import coarse_fine_scanrecord
# # from .plans.step1d_scanrecord import step1d_scanrecord
# # # from .plans.step2d import step2d
# # # from .plans.step1d import step1d


## QServer functions
from .qserver.helper_funcs import get_save_data_path
from .qserver.helper_funcs import get_global_health_snapshot
from .qserver.helper_funcs import get_plan_monitor_snapshot
from .qserver.helper_funcs import recover_detector
from .qserver.helper_funcs import syncXYZ
from .qserver.helper_funcs import syncXYZ_transform


try:
    logger.info("Generating beamline monitor PVs")
    beamline_monitor_manifest = generate_beamline_monitor_manifest(
        oregistry=oregistry,
        output_path=instrument_path / "qserver" / "beamline_monitor.json",
        config_path=instrument_path / "qserver" / "beamline_monitor.yml",
    )
    logger.info("Beamline monitor PVs written to %s", beamline_monitor_manifest)
except Exception:
    logger.exception("Failed to generate beamline monitor PVs")

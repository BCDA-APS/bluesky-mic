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
from apsbits.core.instrument_init import make_devices
from apsbits.core.instrument_init import oregistry
from apsbits.core.run_engine_init import init_RE

# Utility functions
from apsbits.utils.aps_functions import aps_dm_setup
# from apsbits.utils.aps_functions import host_on_aps_subnet

# Configuration functions
from apsbits.utils.config_loaders import load_config
from apsbits.utils.helper_functions import register_bluesky_magics
from apsbits.utils.helper_functions import running_in_queueserver
from apsbits.utils.logging_setup import configure_logging

# Utility functions from apstools and bluesky
from apstools.utils import listobjects
from apstools.utils import listplans
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

# Discard oregistry items loaded above.
oregistry.clear()

# Configure the session with callbacks, devices, and plans.
aps_dm_setup(iconfig.get("DM_SETUP_FILE"))

# Command-line tools, such as %wa, %ct, ...
register_bluesky_magics()

# Bluesky initialization block
# Instrument = ...
# oregistry = ...
# oregistry.clear()
bec, peaks = init_bec_peaks(iconfig)
cat = init_catalog(iconfig)
RE, sd = init_RE(iconfig, bec_instance=bec, cat_instance=cat)


# Optional Nexus callback block
# delete this block if not using Nexus
# if iconfig.get("NEXUS_DATA_FILES", {}).get("ENABLE", False):
from .callbacks.demo_nexus_callback import nxwriter_init
print("iom here \n\n\n\n")
nxwriter = nxwriter_init(RE)

# # These imports must come after the above setup.
# # Queue server block
if running_in_queueserver():
    ### To make all the standard plans available in QS, import by '*', otherwise import
    ### plan by plan.
    from apstools.plans import lineup2  # noqa: F401
    from bluesky.plans import *  # noqa: F403
else:
    # Import bluesky plans and stubs with prefixes set by common conventions.
    # The apstools plans and utils are imported by '*'.
    from apstools.plans import *  # noqa: F403
    from apstools.utils import *  # noqa: F403
    from bluesky import plan_stubs as bps  # noqa: F401
    from bluesky import plans as bp  # noqa: F401


# Experiment specific logic, device and plan loading
# RE(make_devices(clear=False, file="devices.yml"))  # Create the devices.

# if host_on_aps_subnet():
#     RE(make_devices(clear=False, file="device_aps_only.yml"))

# local_mountpath = iconfig.get("STORAGE")["PATH"]
# xrf_netcdf = oregistry["xrf_netcdf"]
# xrf_netcdf.micdata_mountpath = local_mountpath

RE(make_devices(clear=False, file="sim_devices.yml"))

# from .plans.step2d import step2d
# from .plans.fly2d import fly2d

from .plans.sim_plans import sim_count_plan
from .plans.sim_plans import sim_print_plan
from .plans.sim_plans import sim_rel_scan_plan
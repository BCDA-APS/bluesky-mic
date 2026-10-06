"""Initialize BNP Data Management workflows without beamline devices.

Import this module when DM workflow access is needed independently of the
normal BNP Bluesky startup. It intentionally does not initialize Guarneri,
Ophyd devices, the RunEngine, catalogs, detectors, or beamline plans.
"""

import logging
from pathlib import Path

from apsbits.utils.config_loaders import load_config
from apsbits.utils.logging_setup import configure_logging
from apstools.utils.aps_data_management import dm_setup

from mic_common.dm.agent import get_dm_agent
from mic_common.dm.qserver import create_dm_experiment, start_dm_daq
from mic_common.dm.workflow_configs import load_dm_workflow_args


instrument_path = Path(__file__).parent
iconfig_path = instrument_path / "configs" / "iconfig.yml"
iconfig = load_config(iconfig_path)

extra_logging_configs_path = instrument_path / "configs" / "extra_logging.yml"
configure_logging(extra_logging_configs_path=extra_logging_configs_path)

logger = logging.getLogger(__name__)
logger.info("Starting BNP DM-only session with config: %s", iconfig_path)

# Configure the APS Data Management client environment.
dm_setup(iconfig.get("DM_SETUP_FILE"))

# Initialize the shared workflow agent and BNP workflow defaults.
dm_agent = get_dm_agent()

dm_experiment_type = iconfig.get("DM_EXPERIMENT_TYPE_NAME")
if dm_experiment_type:
    dm_agent.set_experiment_type_name(dm_experiment_type)

xrf_workflow_path = instrument_path / "configs" / "xrf_workflow.yml"
xrf_dm_args = load_dm_workflow_args(xrf_workflow_path)
dm_agent.set_workflow_args("xrf", xrf_dm_args)

waitlist_pattern = iconfig.get("DM_XRF_WAITLIST_FILE_PATTERN")
if waitlist_pattern:
    dm_agent.set_waitlist_pattern("xrf", waitlist_pattern)

logger.info("BNP DM agent initialized with XRF workflow arguments from %s", xrf_workflow_path)

__all__ = [
    "create_dm_experiment",
    "dm_agent",
    "iconfig",
    "start_dm_daq",
    "xrf_dm_args",
]

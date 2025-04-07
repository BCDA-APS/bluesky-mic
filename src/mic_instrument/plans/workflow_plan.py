"""
Run DM workflow
"""

import logging
from pathlib import Path

from apstools.utils import share_bluesky_metadata_with_dm

# from .local_scans import mv
from bluesky.plan_stubs import mv
from bluesky.plan_stubs import sleep
from databroker.core import BlueskyRun
from yaml import Loader as yloader
from yaml import load as yload

from ..devices import dm_experiment
from ..devices import dm_workflow

# from ..utils._logging_setup import logger
# from ..utils.catalog import full_cat
from ..utils.catalog import full_cat

logger = logging.getLogger(__name__)
logger.info(__file__)

EXPECTED_KWARGS = {}
EXPECTED_KWARGS["ptychodus"] = [
    "workflow",
    "filePath",
    "sampleName",
    "experimentName",
    "scanFilePath",
    "analysisMachine",
    "detectorName",
    "detectorDistanceInMeters",
    "cropCenterXInPixels",
    "cropCenterYInPixels",
    "cropExtentXInPixels",
    "cropExtentYInPixels",
    "probeEnergyInElectronVolts",
    "numGpus",
    "settings",
    "demand",
    "name",
]

EXPECTED_KWARGS["ptycho-xrf"] = [
    "workflow",
    "experimentName",
    "fit",
    "filePath",
    "dataDir",
    "nthreads",
    "quantifyWith",
    "detectors",
    "generateAvgH5",
    "addv9Layout",
    "addExchange",
    "exportCSV",
    "updateTheta",
    "updateAmps",
    "updateQuantAmps",
    "quickAndDirty",
    "optimizeFitOverrideParams",
    "optimizer",
    "analysisMachine",
    "name",
    "sampleName",
    "ptychoFilePath",
    "ptychoDetectorName",
    "settings",
    "cropCenterXInPixels",
    "cropCenterYInPixels",
    "cropExtentXInPixels",
    "cropExtentYInPixels",
    "numGpus",
    "probeEnergyInElectronVolts",
    "detectorDistanceInMeters",
    "preprocessingMachine",
    "settings",
    "demand",
]

EXPECTED_KWARGS["xrf-maps"] = [
    "workflow",
    "experimentName",
    "fit",
    "filePath",
    "dataDir",
    "nthreads",
    "quantifyWith",
    "detectors",
    "generateAvgH5",
    "addv9Layout",
    "addExchange",
    "exportCSV",
    "updateTheta",
    "updateAmps",
    "updateQuantAmps",
    "quickAndDirty",
    "optimizeFitOverrideParams",
    "optimizer",
    "analysisMachine",
    "demand",
]


def _load_yaml(path):
    """
    Load iconfig.yml (and other YAML) configuration files.

    Parameters
    ----------
    iconfig_yml: str
        Name of the YAML file to be loaded.  The name can be
        absolute or relative to the current working directory.
        Default: ``INSTRUMENT/configs/iconfig.yml``
    """

    if not path.exists():
        raise FileExistsError(f"Configuration file '{path}' does not exist.")

    return yload(open(path, "r").read(), yloader)


def run_workflow(
    bluesky_id=None,
    # internal kwargs ----------------------------------------------------------
    dm_concise: bool = False,
    dm_wait: bool = False,
    dm_reporting_period: float = 10 * 60,
    dm_reporting_time_limit: float = 10**6,
    # Option to import DM workflow kwargs from a file --------------------------
    settings_file_path: str = None,
    # Or you can enter the kwargs that will be just be passed to the workflow --
    **_kwargs,
):
    """Run a DM workflow with specified parameters.

    Parameters:
        bluesky_id: Bluesky run ID or run object.
        dm_concise (bool): Use concise reporting.
        dm_wait (bool): Wait for workflow completion.
        dm_reporting_period (float): Reporting period in seconds.
        dm_reporting_time_limit (float): Maximum reporting time.
        settings_file_path (str): Path to settings file.
        **_kwargs: Additional workflow parameters.

    Raises:
        FileExistsError: If settings file not found.
        ValueError: If required workflow parameters missing.
    """
    # Option to import workflow parameters from file.
    kwargs = {}
    if settings_file_path is not None:
        path = Path(settings_file_path)
        if not path.exists():
            raise FileExistsError(f"Configuration file '{path}' does not exist.")
        kwargs = yload(open(path, "r").read(), yloader)

    # kwargs given in function call will have priority.
    kwargs.update(_kwargs)
    for key in kwargs.keys():  # Clean up "None".
        if kwargs[key] in ("None", "none"):
            kwargs[key] = None

    # Check if kwargs have all argumnents needed.
    workflow = kwargs.get("workflow", None)
    if workflow is None:
        raise ValueError("The 'workflow'  argument is required, but was not found.")
    if workflow not in EXPECTED_KWARGS.keys():
        raise ValueError(
            f"The 'workflow' argument must be one of {EXPECTED_KWARGS.keys()}, "
            f"but {workflow} was entered."
        )

    missing = []
    for required in EXPECTED_KWARGS[workflow]:
        if required not in kwargs.keys():
            missing.append(required)

    if len(missing) > 0:
        raise ValueError(
            "The following arguments were not found, but are required for the "
            f"{workflow} workflow: {missing}."
        )

    # Check that the bluesky_id works.
    if isinstance(bluesky_id, (str, int)):
        try:
            run = full_cat[bluesky_id]
        except KeyError as err:
            raise KeyError(
                "Could not find a Bluesky run associated with the " f"{bluesky_id=}."
            ) from err
    elif isinstance(bluesky_id, BlueskyRun):
        run = bluesky_id
    else:
        logger.warning(
            "Could not find the scan associated to the bluesky_id entered. "
            "Bluesky metadata will not be shared with DM."
        )
        run = None

    # Start workflow
    logger.info(f"DM workflow {workflow}.")

    yield from mv(
        dm_workflow.concise_reporting,
        dm_concise,
        dm_workflow.reporting_period,
        dm_reporting_period,
    )

    yield from dm_workflow.run_as_plan(
        wait=dm_wait, timeout=dm_reporting_time_limit, **kwargs
    )

    yield from sleep(0.1)
    logger.info(f"dm_workflow id: {dm_workflow.job_id.get()}")

    # upload bluesky run metadata to APS DM
    if run is not None:
        share_bluesky_metadata_with_dm(dm_experiment.get(), workflow, run)

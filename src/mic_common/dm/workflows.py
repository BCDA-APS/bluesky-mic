"""Workflow-specific DM submission helpers."""

import logging
import os
from copy import deepcopy
from typing import Any

logger = logging.getLogger(__name__)


def build_default_xrf_download_path(savedata) -> str:
    """Build the default XRF DM download path from a SaveData-like object."""
    return os.path.join(savedata.get_auto_storage_path(), "img.dat")


def submit_xrf_dm_job(
    file_path: str,
    analysis_machine: str,
    experiment_name: str,
    download: str | None = None,
    workflow_args: dict[str, Any] | None = None,
    workflow_name: str = "xrf-maps",
    verbose: bool = True,
) -> dict[str, Any]:
    """Submit an XRF MDA file to a DM XRF workflow."""
    from .agent import get_dm_agent

    dm_agent = get_dm_agent()
    if workflow_args is None:
        workflow_args = dm_agent.get_workflow_args("xrf")

    args = deepcopy(workflow_args)
    args["filePath"] = file_path
    args["analysisMachine"] = analysis_machine
    args["experimentName"] = experiment_name
    if download is not None:
        args["download"] = download

    job = dm_agent.start_processing_job(workflow_name, args)
    if verbose:
        logger.info("Started DM %s job for %s: %s", workflow_name, file_path, job)
    return job

"""Bluesky plan wrappers for DM workflow submission."""

from typing import Any

from bluesky import plan_stubs as bps

from .validation import validate_xrf_dm_inputs
from .workflows import build_default_xrf_download_path
from .workflows import submit_xrf_dm_job


def submit_xrf_dm_job_plan(
    file_path: str,
    analysis_machine: str,
    experiment_name: str,
    download: str | None = None,
    savedata=None,
    workflow_args: dict[str, Any] | None = None,
    workflow_name: str = "xrf-maps",
    verbose: bool = True,
    check_file_readiness: bool = False,
    waitlist_folder: str | None = None,
    waitlist_pattern: str | None = None,
    validate_workflow_args: bool = True,
) -> dict[str, Any]:
    """Submit an XRF MDA file to DM from inside a Bluesky plan."""
    if download is None and savedata is not None:
        download = build_default_xrf_download_path(savedata)

    validate_xrf_dm_inputs(analysis_machine, experiment_name, download)

    yield from bps.null()
    return submit_xrf_dm_job(
        file_path,
        analysis_machine,
        experiment_name,
        download=download,
        workflow_args=workflow_args,
        workflow_name=workflow_name,
        verbose=verbose,
        check_file_readiness=check_file_readiness,
        waitlist_folder=waitlist_folder,
        waitlist_pattern=waitlist_pattern,
        validate_workflow_args=validate_workflow_args,
    )

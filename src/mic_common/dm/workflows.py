"""Workflow-specific DM submission helpers."""

import logging
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def build_default_xrf_download_path(savedata) -> str:
    """Build the default XRF DM download path from a SaveData-like object."""
    return os.path.join(savedata.get_auto_storage_path(), "img.dat")


def build_xrf_waitlist(
    file_path: str,
    waitlist_folder: str | Path,
    waitlist_pattern: str,
) -> str:
    """Build a comma-separated DM waitlist from matching files."""
    mda_path = Path(file_path)
    match = re.fullmatch(r"(?P<prefix>.*?)(?P<scan_number>\d+)", mda_path.stem)
    format_values = {
        "stem": mda_path.stem,
        "name": mda_path.name,
        "prefix": match.group("prefix") if match else mda_path.stem,
        "scan_number": str(int(match.group("scan_number"))) if match else "",
        "scan_number_padded": match.group("scan_number") if match else "",
    }
    pattern = waitlist_pattern.format(**format_values)
    matches = sorted(Path(waitlist_folder).glob(pattern))
    if not matches:
        raise FileNotFoundError(
            f"No XRF waitlist files found in {waitlist_folder!s} "
            f"with pattern {pattern!r}."
        )
    return ",".join(match.name for match in matches)


def submit_xrf_dm_job(
    file_path: str,
    analysis_machine: str,
    experiment_name: str,
    download: str | None = None,
    waitlist: str | None = None,
    workflow_args: dict[str, Any] | None = None,
    workflow_name: str = "xrf-maps",
    verbose: bool = True,
    check_file_readiness: bool = False,
    waitlist_folder: str | Path | None = None,
    waitlist_pattern: str | None = None,
    validate_workflow_args: bool = True,
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
    if waitlist is not None:
        args["waitlist"] = waitlist
    elif check_file_readiness:
        if waitlist_pattern is None:
            try:
                waitlist_pattern = dm_agent.get_waitlist_pattern("xrf")
            except KeyError:
                waitlist_pattern = None
        if waitlist_folder is None:
            raise ValueError(
                "waitlist_folder is required when check_file_readiness is True "
                "and waitlist is not provided."
            )
        if not waitlist_pattern:
            raise ValueError(
                "waitlist_pattern is required when check_file_readiness is True "
                "and waitlist is not provided."
            )
        args["waitlist"] = build_xrf_waitlist(
            file_path,
            waitlist_folder,
            waitlist_pattern,
        )

    job = dm_agent.start_processing_job(
        workflow_name,
        args,
        validate_workflow_args=validate_workflow_args,
    )
    if verbose:
        logger.info("Started DM %s job for %s: %s", workflow_name, file_path, job)
    return job

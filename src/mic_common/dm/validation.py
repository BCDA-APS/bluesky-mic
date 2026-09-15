"""Validation helpers for DM workflow submission."""

XRF_ANALYSIS_MACHINES = {"polaris", "mona3", "mona4", "xfm3"}


def validate_xrf_dm_inputs(
    analysis_machine: str,
    experiment_name: str,
    download: str | None = None,
) -> None:
    """Validate XRF DM submission inputs before starting a job."""
    if not isinstance(analysis_machine, str) or not analysis_machine.strip():
        raise ValueError("dm_analysis_machine is required for XRF DM submission.")
    if analysis_machine not in XRF_ANALYSIS_MACHINES:
        raise ValueError(
            f"dm_analysis_machine must be one of {sorted(XRF_ANALYSIS_MACHINES)}; "
            f"received {analysis_machine!r}."
        )
    if not isinstance(experiment_name, str) or not experiment_name.strip():
        raise ValueError("dm_experiment_name is required for XRF DM submission.")
    if download is not None and (not isinstance(download, str) or not download.strip()):
        raise ValueError("dm_download must be a non-empty string when provided.")

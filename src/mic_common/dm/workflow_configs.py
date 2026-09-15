"""Helpers for loading DM workflow argument configuration."""

import logging
from pathlib import Path
from typing import Any

from apsbits.utils.config_loaders import load_config_yaml

logger = logging.getLogger(__name__)


def load_dm_workflow_args(config_path: str | Path) -> dict[str, Any]:
    """Load a DM workflow argument YAML file."""
    config_path = Path(config_path)
    workflow_args = load_config_yaml(config_path)
    logger.info("Loaded DM workflow args from %s", config_path)
    return workflow_args

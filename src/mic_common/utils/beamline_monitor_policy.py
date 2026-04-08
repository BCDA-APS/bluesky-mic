"""Shared interfaces for worker-side beamline monitor enrichment."""

from __future__ import annotations

from typing import Any, Mapping, Protocol


class BeamlineMonitorPolicy(Protocol):
    """Policy for beamline-specific monitor enrichment."""

    def enrich_device(self, device_name: str, device: Mapping[str, Any], snapshot: Mapping[str, Any]) -> dict[str, Any]:
        """Return enriched device metadata such as role, health, summary, and actions."""

    def summarize_activity(self, snapshot: Mapping[str, Any]) -> str:
        """Return a short snapshot-wide activity string."""


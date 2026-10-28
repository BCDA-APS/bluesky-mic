"""Evaluation functions shared by S2IDD Blop agents."""

from collections.abc import Mapping, Sequence
from typing import Any

from s2idd_auto.blop_runtime import get_catalog


def evaluate_scaler(uid: str, suggestions: Sequence[Mapping[str, Any]]):
    """Return USIC and DSIC outcomes for a scaler acquisition run."""
    run = get_catalog()[uid]
    dataset = run.primary.read()
    try:
        start = run.start
    except AttributeError:
        start = run.metadata["start"]

    acquisition_order = start.get("blop_acquisition_order")
    if acquisition_order is None:
        blop_suggestions = start.get("blop_suggestions", suggestions)
        acquisition_order = [suggestion["_id"] for suggestion in blop_suggestions]

    usic = dataset["joerger_scaler_usic_counts"].values
    dsic = dataset["joerger_scaler_dsic_counts"].values
    if len(acquisition_order) != len(usic) or len(usic) != len(dsic):
        raise ValueError(
            "Blop acquisition order and scaler data have different lengths: "
            f"order={len(acquisition_order)}, usic={len(usic)}, dsic={len(dsic)}"
        )

    return [
        {
            "_id": suggestion_id,
            "usic_counts": float(usic[index]),
            "dsic_counts": float(dsic[index]),
        }
        for index, suggestion_id in enumerate(acquisition_order)
    ]

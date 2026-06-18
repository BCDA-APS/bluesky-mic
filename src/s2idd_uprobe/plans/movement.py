"""Plans for moving sample and zone-plate axes to target positions."""

from __future__ import annotations

from apsbits.core.instrument_init import oregistry
from bluesky import plan_stubs as bps

sample = oregistry["sample"]
zp_z = oregistry["zp_z"]


def move_sample(axis: str, position: float):
    axis_name = str(axis).strip().lower()
    if axis_name not in {"x", "y", "z"}:
        raise ValueError("axis must be one of 'x', 'y', or 'z'")
    motor = getattr(sample, axis_name)
    position_value = float(position)
    yield from bps.mv(motor, position_value)
    return float(motor.position)


def move_zp_z(position: float):
    position_value = float(position)
    yield from bps.mv(zp_z, position_value)
    return float(zp_z.position)

"""Plans for moving sample and zone-plate axes to target positions."""

from __future__ import annotations

from apsbits.core.instrument_init import oregistry
from bluesky import plan_stubs as bps

sample = oregistry["sample"]
zp_z = oregistry["zp_z"]
osa = oregistry["osa"]


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


def move_osa_absolute(x_mm: float, y_mm: float):
    """Move the OSA to an absolute position (x, y) in mm."""
    x_value = float(x_mm)
    y_value = float(y_mm)
    yield from bps.mv(osa.x, x_value, osa.y, y_value)
    return float(osa.x.position), float(osa.y.position)

def read_osa_position():
    """Read the current OSA position in um."""
    x_position = float(osa.x.position) 
    y_position = float(osa.y.position)
    return x_position, y_position
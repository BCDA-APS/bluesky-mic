"""Plans for moving sample and zone-plate axes to target positions."""

from __future__ import annotations

from apsbits.core.instrument_init import oregistry
from bluesky import plan_stubs as bps

from .read_dsic_counts import read_dsic_counts

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


def move_osa_absolute(x_mm: float, y_mm: float, return_cts: bool = False):
    """Move the OSA to absolute (x, y) in mm, optionally measuring DSIC.

    Return the final (x, y) positions by default. With ``return_cts=True``,
    acquire one 1-second DSIC measurement after both moves finish and return
    ``(x_position, y_position, dsic_counts)``. Plan return values are available through
    ``yield from`` or a RunEngine configured with ``call_returns_result=True``.
    """

    x_value = float(x_mm)
    y_value = float(y_mm)
    yield from bps.mv(osa.x, x_value, osa.y, y_value)
    if return_cts:
        counts = yield from read_dsic_counts()
        return float(osa.x.position), float(osa.y.position), counts
    return float(osa.x.position), float(osa.y.position)

def read_osa_position():
    """Read the current OSA position in um."""
    
    x_position = float(osa.x.position) 
    y_position = float(osa.y.position)
    return x_position, y_position

"""Coordinate transform helpers for BNP sample motions."""

from __future__ import annotations

from math import cos, pi, sin


def coordinate_transform(
    theta: float,
    x: float,
    y: float,
    z: float,
    *,
    xo: float,
    yo: float,
    zo: float,
    xa: float,
    ya: float,
    za: float,
) -> dict[str, float]:
    """Transform theta-0 sample coordinates into scan coordinates at ``theta``."""

    theta_radians = theta * (pi / 180.0)
    cosine_factor = cos(theta_radians)
    sine_factor = sin(theta_radians)

    # Match the legacy two-step transform:
    # 1. Treat the provided x/y/z as drive coordinates at theta=0.
    # 2. Convert to axis coordinates, then rotate to the requested angle.
    x_axis = -xo - x + xa
    y_axis = -yo - y + ya
    z_axis = -zo - z + za
    fine_x_axis = x_axis
    fine_y_axis = y_axis

    z_drive = (
        -(zo * cosine_factor)
        + (fine_x_axis * sine_factor)
        - (z_axis * cosine_factor)
        + (xo * sine_factor)
        + za
    )
    fine_x_drive = (
        -(xo * cosine_factor)
        - (fine_x_axis * cosine_factor)
        - (z_axis * sine_factor)
        - (zo * sine_factor)
        + xa
    )
    fine_y_drive = -yo - fine_y_axis + ya

    return {
        "theta": round(float(theta), 4),
        "x": round(float(fine_x_drive), 4),
        "y": round(float(fine_y_drive), 4),
        "z": round(float(z_drive), 4),
    }

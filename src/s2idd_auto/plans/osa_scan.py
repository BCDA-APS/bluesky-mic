"""OSA scan plans."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable

import bluesky.plan_stubs as bps
from apsbits.core.instrument_init import oregistry

logger = logging.getLogger(__name__)

osa = oregistry["osa"]


def _scan_positions_um(center_um: float, width_um: float, points: int) -> list[float]:
    if points < 1:
        raise ValueError("points must be at least 1")
    if points == 1:
        return [center_um]

    start_um = center_um - width_um / 2
    step_um = width_um / (points - 1)
    return [start_um + index * step_um for index in range(points)]


def _format_um_for_filename(value_um: float) -> str:
    text = str(round(value_um)).replace("-", "m")
    return f"{text}um"


def osa_xeye_grid_scan(
    x_points: int = 7,
    y_points: int = 7,
    width_um: float = 30,
    height_um: float = 30,
    center_x_um: float | None = None,
    center_y_um: float | None = None,
    settle_time: float = 0.2,
):
    """Scan OSA x/y over a micrometer grid and collect one X-eye TIFF per point
    
    Parameters
    ----------
    x_points: int
        Number of points in the x-direction. Default: 7.
    y_points: int
        Number of points in the y-direction. Default: 7.
    width_um: float
        Total width of the scan area in microns. Default: 30.
    height_um: float
        Total height of the scan area in microns. Default: 30.
    center_x_um: float | None
        Center position of the scan in the x-direction in microns. If None, use current OSA x position. Default: None.
    center_y_um: float | None
        Center position of the scan in the y-direction in microns. If None, use current OSA y position. Default: None.
    settle_time: float
        Time in seconds to wait after moving to a new position before acquiring the image. Default: 0.2.    
    
    """

    from s2idd_uprobe.qserver.xeye_osa import acquire_xeye_image

    x_count = int(x_points)
    y_count = int(y_points)
    x_center_um = float(osa.x.position) * 1000 if center_x_um is None else float(center_x_um)
    y_center_um = float(osa.y.position) * 1000 if center_y_um is None else float(center_y_um)

    x_positions_um = _scan_positions_um(x_center_um, float(width_um), x_count)
    y_positions_um = _scan_positions_um(y_center_um, float(height_um), y_count)

    logger.info(
        "Starting OSA X-eye grid scan: x=%s um, y=%s um",
        x_positions_um,
        y_positions_um,
    )
    scan_id = time.strftime("%Y%m%d_%H%M%S")
    for y_index, y_um in enumerate(y_positions_um):
        x_iterable: Iterable[float]
        x_iterable = reversed(x_positions_um) if y_index % 2 else x_positions_um
        for x_um in x_iterable:
            x_mm = x_um / 1000
            y_mm = y_um / 1000
            yield from bps.mv(osa.x, x_mm, osa.y, y_mm)
            if settle_time > 0:
                yield from bps.sleep(settle_time)

            filename = (
                f"xeye_osa_{scan_id}_"
                f"x_{_format_um_for_filename(x_um)}_"
                f"y_{_format_um_for_filename(y_um)}.tiff"
            )
            result = acquire_xeye_image(filename=filename)
            if not result.get("success"):
                raise RuntimeError(f"X-eye image acquisition failed: {result.get('error')}")
            yield from bps.checkpoint()

    return {
        "x_positions_um": x_positions_um,
        "y_positions_um": y_positions_um,
    }

"""Helpers for coarse-to-fine BNP scan workflows."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import h5py
import numpy as np
from scipy.ndimage import center_of_mass

logger = logging.getLogger(__name__)


def resolve_coarse_h5_path(base_dir: str | Path, scan_name: str) -> Path:
    """Return the expected HDF5 output path for a coarse scan."""

    base_path = Path(base_dir)
    scan_path = Path(scan_name)
    candidates = [
        base_path / "img.dat" / f"{scan_name}.h5",
        base_path / "img.dat" / f"{scan_path.stem}.h5",
        base_path / f"{scan_name}.h5",
        base_path / f"{scan_path.stem}.h5",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def wait_for_coarse_h5(
    base_dir: str | Path,
    scan_name: str,
    *,
    timeout: float = 30.0,
    poll_interval: float = 1.0,
) -> Path:
    """Wait until the expected coarse HDF5 file exists and stabilizes."""

    deadline = time.monotonic() + timeout
    last_size: int | None = None
    stable_reads = 0
    candidate = resolve_coarse_h5_path(base_dir, scan_name)

    while time.monotonic() < deadline:
        candidate = resolve_coarse_h5_path(base_dir, scan_name)
        print(f"Waiting for coarse scan file '{candidate}'")
        if candidate.exists():
            size = candidate.stat().st_size
            if size > 0 and size == last_size:
                stable_reads += 1
                if stable_reads >= 2:
                    return candidate
            else:
                stable_reads = 0
                last_size = size
        time.sleep(poll_interval)

    raise TimeoutError(f"Timed out waiting for coarse scan file '{candidate}'")


def get_coordinate(
    coarse_h5_path: str | Path,
    *,
    elm: str,
    mask_elm: str | None = None,
    use_mask: bool = False,
    n_std: float = 2.0,
) -> tuple[float, float]:
    """Return a fine-scan ``(x_center, y_center)`` from a coarse scan HDF5 file."""

    coarse_h5_path = Path(coarse_h5_path)
    with h5py.File(coarse_h5_path, "r") as handle:
        xrf_path = "/MAPS/XRF_roi_plus" if "/MAPS/XRF_roi_plus" in handle else "/MAPS/XRF_roi"
        channel_names = _decode_channel_names(handle["/MAPS/channel_names"][:])
        x_pos = np.asarray(handle["/MAPS/x_axis"][:], dtype=float)
        y_pos = np.asarray(handle["/MAPS/y_axis"][:], dtype=float)
        elmmap = np.asarray(handle[xrf_path][channel_names.index(elm), :, :], dtype=float)

        mask = np.ones(elmmap.shape, dtype=bool)
        if use_mask and mask_elm:
            maskmap = np.asarray(handle[xrf_path][channel_names.index(mask_elm), :, :], dtype=float)
            mask_threshold = np.nanmean(maskmap) + float(n_std) * np.nanstd(maskmap)
            mask = maskmap < mask_threshold

    signal = np.where(np.isfinite(elmmap), elmmap, 0.0)
    if use_mask and mask_elm:
        signal = np.where(mask, signal, 0.0)

    threshold = np.nanmean(signal) + np.nanstd(signal)
    roi = signal > threshold
    if np.any(roi):
        weighted = np.where(roi, signal, 0.0)
        row, col = center_of_mass(weighted)
    else:
        row, col = np.unravel_index(np.nanargmax(signal), signal.shape)

    x_center = float(np.interp(float(col), np.arange(len(x_pos), dtype=float), x_pos))
    y_center = float(np.interp(float(row), np.arange(len(y_pos), dtype=float), y_pos))
    logger.info("Resolved fine-scan center from '%s': x=%.2f y=%.2f", coarse_h5_path, x_center, y_center)
    return round(x_center, 2), round(y_center, 2)


def _decode_channel_names(raw_names: np.ndarray) -> list[str]:
    decoded: list[str] = []
    for entry in raw_names:
        if isinstance(entry, bytes):
            decoded.append(entry.decode("utf-8", errors="ignore").strip())
        else:
            decoded.append(str(entry).strip())
    return decoded

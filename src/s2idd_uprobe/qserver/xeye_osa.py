"""QServer helper to grab a live frame from the X-eye (OSA) camera.

The X-eye is an Axis IP camera viewed in a browser over an RTSP-over-WebSocket
stream. Rather than reimplement that transport, this helper hits the camera's
native Axis snapshot CGI (a plain HTTP GET that returns one fresh JPEG per
request, served with no-cache headers) and writes the frame to disk as TIFF.
"""

from __future__ import annotations

import logging
import time
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image

from .helper_funcs import get_save_data_path

logger = logging.getLogger(__name__)

# Axis snapshot CGI: each GET triggers a fresh sensor capture (no caching).
XEYE_CAMERA_URL = "http://10.54.113.158/axis-cgi/jpg/image.cgi"

# Subdirectory (under the save-data path) where X-eye frames are stored.
XEYE_SUBDIR = "xeye"


def acquire_xeye_image(
    url: str = XEYE_CAMERA_URL,
    filename: str | None = None,
    timeout: float = 6.0,
) -> dict[str, object]:
    """Grab one live frame from the X-eye camera and save it as a TIFF.

    The frame is written to an ``xeye`` subdirectory of the current QueueServer
    save-data path (``get_save_data_path()``). When ``filename`` is omitted a
    timestamped name is used.

    Returns a dict with ``success`` and, on success, ``img_path``,
    ``size_bytes``, and ``source``. On failure it returns ``success: False``
    with an ``error`` message instead of raising.
    """
    try:
        parent = get_save_data_path()
        if parent is None:
            return {
                "success": False,
                "error": "savedata device unavailable; cannot resolve save-data path",
                "source": url,
            }

        out_dir = Path(parent) / XEYE_SUBDIR
        out_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            filename = f"xeye_{time.strftime('%Y%m%d_%H%M%S')}.tiff"
        out_path = (out_dir / filename).with_suffix(".tiff")

        # cache-bust to defeat any intermediate caching; Axis serves a fresh
        # capture per request regardless, but this is belt-and-suspenders.
        request = urllib.request.Request(f"{url}?cachebust={time.time()}")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            image_bytes = response.read()

        with Image.open(BytesIO(image_bytes)) as image:
            image.save(out_path, format="TIFF")

        size_bytes = out_path.stat().st_size
        logger.info("X-eye frame saved to %s (%d bytes)", out_path, size_bytes)

        return {
            "success": True,
            "img_path": str(out_path),
            "size_bytes": size_bytes,
            "source": url,
        }
    except Exception as exc:
        logger.exception("Failed to acquire X-eye image")
        return {
            "success": False,
            "error": str(exc),
            "source": url,
        }

"""Simulated detector devices and HDF5 plugin utilities."""

import logging
from functools import wraps
from typing import Any
from typing import Generator

import bluesky.plan_stubs as bps
from ophyd.areadetector.cam import SimDetectorCam
from ophyd.areadetector.plugins import HDF5Plugin

logger = logging.getLogger(__name__)
logger.info(__file__)


def value_setter(attribute_name: str) -> Any:
    """Decorator to set a value for an EpicsSignal."""

    def decorator(func: Any) -> Any:
        @wraps(func)
        def wrapper(self: Any, value: Any) -> Generator:
            signal = getattr(self, attribute_name)
            try:
                yield from bps.mv(signal, value)
                logger.info(f"Assigned {attribute_name} in {self.prefix} to {value}.")
            except Exception as e:
                logger.error(
                    f"Error setting {attribute_name} to {value} in {self.prefix}: {e}"
                )

        return wrapper

    return decorator


class SimDet(SimDetectorCam):
    """Simulated detector camera."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize SimDet."""
        super().__init__(*args, **kwargs)


class SimDetHDF5(HDF5Plugin):
    """HDF5 plugin for simulated detectors."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize SimDetHDF5."""
        super().__init__(*args, **kwargs)

    @value_setter("file_path")
    def set_filepath(self, path: str) -> None:
        """Set HDF5 file path."""
        pass

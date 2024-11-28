from ophyd.areadetector.cam import SimDetectorCam
from ophyd.areadetector.plugins import HDF5Plugin
from functools import wraps
import logging


logger = logging.getLogger(__name__)
logger.info(__file__)


def value_setter(attribute_name):
    """Decorator to set value for EpicsSignal component."""

    def decorator(func):
        @wraps(func)
        def wrapper(self, value):
            signal = getattr(self, attribute_name)
            try:
                yield from bps.mv(signal, value)
                logger.info(f"Assigned {attribute_name} in {self.prefix} to {value}.")
            except Exception as e:
                logger.error(f"Error setting {attribute_name} to {value} in {self.prefix}: {e}")

        return wrapper

    return decorator


class SimDet(SimDetectorCam):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SimDetHDF5(HDF5Plugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @value_setter("file_path")
    def set_filepath(self, path):
        pass

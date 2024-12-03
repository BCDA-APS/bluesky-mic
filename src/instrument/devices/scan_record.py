# __all__ = """
#     scan1
#     scan2
# """.split()

from apstools.synApps import SscanRecord
from ophyd import EpicsSignal, Component
from epics import PV
from functools import wraps
import bluesky.plan_stubs as bps
import logging


logger = logging.getLogger(__name__)
logger.info(__file__)


def mode_setter(attribute_name):
    """Decorator to set mode for EpicsSignal component using enum states."""

    def decorator(func):
        @wraps(func)
        def wrapper(self, mode):
            # Retrieve the EpicsSignal component
            signal = getattr(self, attribute_name)
            try:
                describe = signal.describe().popitem()
                states = describe[1]["enum_strs"]
                mode = mode.upper()

                # Check if the mode is valid and perform the set operation
                if mode in states:
                    idx = states.index(mode)
                    yield from bps.mv(signal, idx)
                    logger.info(f"Assigned {attribute_name} in {self.prefix} to {mode}.")
                else:
                    logger.error(
                        f"Invalid mode: {mode} for {attribute_name} in {self.prefix}. "
                        f"Available states: {states}"
                    )
            except Exception as e:
                logger.error(f"Error setting mode for {attribute_name} in {self.prefix}: {e}")

        return wrapper

    return decorator


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


class ScanRecord(SscanRecord):
    scan_mode = Component(EpicsSignal, ".P1SM")
    scan_movement = Component(EpicsSignal, ".P1AR")
    center = Component(EpicsSignal, ".P1CP")
    stepsize = Component(EpicsSignal, ".P1SI")
    width = Component(EpicsSignal, ".P1WD")
    number_points_rbv = Component(EpicsSignal, ".CPT")
    # filesystem = Component(EpicsSignal, ".saveData_fileSystem")
    # basename = Component(EpicsSignal, ".saveData_baseName")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.P1PA = PV(f"{self.prefix}.P1PA")

    def set_center_width_stepsize(self, center: float, width: float, ss: float):
        """Set center, width, and stepsize in a single motion command."""
        try:
            yield from bps.mv(self.center, center, self.width, width, self.stepsize, ss)
            logger.info(f"Set center to {center}, width to {width}, and stepsize to {ss} in {self.prefix}.")
        except Exception as e:
            logger.error(f"Error setting center, width, and stepsize in {self.prefix}: {e}")

    @mode_setter("scan_mode")
    def set_scan_mode(self, mode):
        pass

    @mode_setter("scan_movement")
    def set_rel_abs_motion(self, mode):
        pass

    @value_setter("center")
    def set_center(self, value):
        pass

    @value_setter("width")
    def set_width(self, width):
        pass

    @value_setter("stepsize")
    def set_stepsize(self, stepsize):
        pass

    @value_setter("number_points")
    def set_numpts(self, numpts):
        pass

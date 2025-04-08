"""Utility functions for device configuration and control."""

import logging
from functools import wraps

import bluesky.plan_stubs as bps

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
                states = [s.upper() for s in states]
                mode = mode.upper()

                # Check if the mode is valid and perform the set operation
                if mode in states:
                    idx = states.index(mode)
                    yield from bps.mv(signal, idx)
                    logger.info(f"Availble modes for {signal.pvname}: {states}")
                    logger.info(f"Assigned {signal.pvname} to {mode}.")
                else:
                    logger.error(
                        f"Invalid mode: {mode} for {attribute_name} in {self.prefix}. "
                        f"Available states: {states}"
                    )
            except Exception as e:
                logger.error(
                    f"Error setting mode for {attribute_name} in {self.prefix}: {e}"
                )

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
                logger.info(f"Assigned {signal.pvname} to {value}.")
            except Exception as e:
                logger.error(
                    f"Error setting {attribute_name} to {value} in {self.prefix}: {e}"
                )

        return wrapper

    return decorator

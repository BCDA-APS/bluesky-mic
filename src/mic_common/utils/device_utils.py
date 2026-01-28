"""Utility functions for device configuration and control."""

import logging
from functools import wraps

import bluesky.plan_stubs as bps

logger = logging.getLogger(__name__)
logger.info(__file__)


class LoggingStageSigs(dict):
    """A dictionary that logs all item assignments."""

    def __init__(self, *args, prefix="", **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = prefix

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        logger.info(f"Staging: {self.prefix}['{key}'] = {value} ")

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        for key, value in dict(*args, **kwargs).items():
            logger.info(f"Staging: {self.prefix}['{key}'] = {value} ")

    def clear(self):
        logger.info(f"Clearing stage signals for {self.prefix}")
        super().clear()


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
                    logger.debug(f"Availble modes for {signal.pvname}: {states}")
                    logger.debug(f"Assigned {signal.pvname} to {mode}.")
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
                logger.debug(f"Assigned {signal.pvname} to {value}.")
            except Exception as e:
                logger.error(f"Error setting {attribute_name} to {value} in {self.prefix}: {e}")

        return wrapper

    return decorator


def unstage_with_skip(device, fields_to_skip):
    """
    Helper function to prepare a device for unstage by skipping restoration of specified fields.

    Ophyd stores original values in _original_vals during stage(). To prevent
    certain signals from being restored, this function removes them from both
    stage_sigs and _original_vals. After calling this, you should call
    super().unstage() in your device's unstage() method.

    Parameters:
    -----------
    device : ophyd.Device
        The device instance to prepare for unstage
    fields_to_skip : list of str
        List of field names (attribute names) to exclude from unstage restoration

    Example:
    --------
    def unstage(self):
        fields_to_skip = ['file_path', 'file_name']
        unstage_with_skip(self, fields_to_skip)
        return super().unstage()
    """
    # Get signal objects for fields to skip
    signals_to_skip = {}
    for field in fields_to_skip:
        signal_obj = getattr(device, field, None)
        if signal_obj is not None:
            signals_to_skip[field] = signal_obj

    # Remove from stage_sigs
    for field in fields_to_skip:
        device.stage_sigs.pop(field, None)

    # Remove from _original_vals if it exists (ophyd's internal storage)
    # _original_vals uses signal objects as keys
    if hasattr(device, "_original_vals") and device._original_vals:
        # Create a list of keys to remove (can't modify dict while iterating)
        keys_to_remove = []
        for key in device._original_vals.keys():
            # Check if this key matches any of our signals to skip
            for field, signal_obj in signals_to_skip.items():
                if key is signal_obj or (hasattr(key, "name") and key.name == signal_obj.name):
                    keys_to_remove.append(key)
                    break

        # Remove the keys
        for key in keys_to_remove:
            del device._original_vals[key]

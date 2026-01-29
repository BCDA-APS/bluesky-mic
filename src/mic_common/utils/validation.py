from apsbits.core.instrument_init import oregistry
from ophyd import Device


def validate_scan_parameters(stepsize_x=None, stepsize_y=None, width=None, height=None, dwell_ms=None):
    """
    Validate common scan parameters.

    Parameters
    ----------
    stepsize_x : float
        Step size in x direction
    stepsize_y : float
        Step size in y direction
    width : float
        Width of the scan
    height : float
        Height of the scan
    dwell_ms : float
        Dwell time in ms

    Raises
    ------
    ValueError
        If step sizes are invalid
    """
    if stepsize_x is not None and stepsize_x == 0:
        raise ValueError("Step size cannot be 0, please check the input parameters")
    if stepsize_y is not None and stepsize_y == 0:
        raise ValueError("Step size cannot be 0, please check the input parameters")
    if width is not None and width == 0:
        raise ValueError("Width cannot be 0, please check the input parameters")
    if height is not None and height == 0:
        raise ValueError("Height cannot be 0, please check the input parameters")
    if dwell_ms is not None and dwell_ms == 0:
        raise ValueError("Dwell time cannot be 0, please check the input parameters")


def validate_device_connections(
    det_bools: list[bool], det_names: list[str], return_devices: bool = False
) -> list[Device]:
    """
    Validate that required devices are connected.

    Raises
    ------
    ValueError
        If any required device is not connected
    """
    devices = []

    for det_bool, det_name in zip(det_bools, det_names):
        if det_bool:
            try:
                det = oregistry[det_name]
                if not det.connected:
                    raise ValueError(f"{det.name} is not connected, please check the status")
                devices.append(det)
            except KeyError:
                raise ValueError(f"{det_name} is not connected, please check the status")

    if return_devices:
        return devices
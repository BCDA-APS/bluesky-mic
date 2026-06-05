from logging import getLogger
from apsbits.core.instrument_init import oregistry
import bluesky.plan_stubs as bps
from ..utils.run_engine import peaks, cat

logger = getLogger(__name__)
logger.info(__file__)

__all__ = [
    "maxi",
    "cen",
    "cen2",
    "maxi2",
    "mini2",
]


# TODO: read the positioner from hints? Would need a way to convert the name
# into the actual python object.
def cen(positioner, detector=None):
    """
    Plan that moves motor to center of last scan.

    Uses the position found by the
    `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.

    Parameters
    ----------
    positioner : ophyd instance
        Device to be moved to center.
    detector : str, optional
        Ophyd instance name of the detector used to center. This is only needed
        if the scan had more than one hinted detector.
    """
    if detector is None:
        if len(peaks["cen"].keys()) > 1:
            raise TypeError(
                "You need to provide a detector name if more than 1 detector "
                "was plotted."
            )
        else:
            pos = peaks["cen"][list(peaks["cen"].keys())[0]]
    else:
        pos = peaks["cen"][detector]

    if hasattr(positioner, "position"):
        current_pos = positioner.position
    elif hasattr(positioner, "readback"):
        current_pos = positioner.readback.get()
    else:
        current_pos = positioner.get()
    print("Moving {} from {} to {}".format(positioner.name, current_pos, pos))

    yield from bps.mov(positioner, pos)


def maxi(positioner, detector=None):
    """
    Plan that moves motor to the maximum of last scan.

    Uses the position found by the
    `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.

    Parameters
    ----------
    positioner : ophyd instance
        Device to be moved to center.
    detector : str, optional
        Ophyd instance name of the detector used to center. This is only needed
        if the scan had more than one hinted detector.
    """
    if detector is None:
        if len(peaks["cen"].keys()) > 1:
            raise TypeError(
                "You need to provide a detector name if more than 1 detector "
                "was plotted"
            )
        else:
            pos = peaks["max"][list(peaks["cen"].keys())[0]][0]
    else:
        pos = peaks["max"][detector][0]

    if hasattr(positioner, "position"):
        current_pos = positioner.position
    elif hasattr(positioner, "readback"):
        current_pos = positioner.readback.get()
    else:
        current_pos = positioner.get()
    print("Moving {} from {} to {}".format(positioner.name, current_pos, pos))

    yield from bps.mov(positioner, pos)


def _get_positioner():
    dimensions = cat[-1].metadata["start"]["hints"]["dimensions"]
    if len(dimensions) > 1:
        raise ValueError(
            "Positioner must be specified for scans with more than one "
            "dimension."
        )

    return oregistry.find(dimensions[0][0][0])


def _get_detector():
    if len(peaks["cen"].keys()) > 1:
        raise TypeError(
            "You need to provide a detector name if more than 1 detector "
            "was plotted."
        )

    return peaks["cen"][list(peaks["cen"].keys())[0]]


def _get_current_pos(positioner):
    if hasattr(positioner, "position"):
        current_pos = positioner.position
    elif hasattr(positioner, "readback"):
        current_pos = positioner.readback.get()
    else:
        current_pos = positioner.get()

    return current_pos


def _move_to_pos(parameter, positioner=None, detector=None):

    if positioner is None:
        positioner = _get_positioner()

    if detector is None:
        detector = _get_detector()

    new_pos = peaks[parameter][detector]
    current_pos = _get_current_pos(positioner)

    logger.info(
        "Moving {} from {} to {}".format(positioner.name, current_pos, new_pos)
    )

    yield from bps.mov(positioner, new_pos)


def cen2(positioner=None, detector=None):
    """
    Plan that moves motor to center of last scan.

    Uses the position found by the
    `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.

    Parameters
    ----------
    positioner : ophyd instance, optional
        Device to be moved to center.
    detector : str, optional
        Ophyd instance name of the detector used to center. This is only needed
        if the scan had more than one hinted detector.
    """

    yield from _move_to_pos("cen", positioner=positioner, detector=detector)


def maxi2(positioner=None, detector=None):
    """
    Plan that moves motor to maximum of last scan.

    Uses the position found by the
    `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.

    Parameters
    ----------
    positioner : ophyd instance, optional
        Device to be moved to center.
    detector : str, optional
        Ophyd instance name of the detector used to center. This is only needed
        if the scan had more than one hinted detector.
    """

    yield from _move_to_pos("max", positioner=positioner, detector=detector)


def mini2(positioner=None, detector=None):
    """
    Plan that moves motor to minimum of last scan.

    Uses the position found by the
    `bluesky.callbacks.best_effort.BestEffortCallback().peaks`.

    Parameters
    ----------
    positioner : ophyd instance, optional
        Device to be moved to center.
    detector : str, optional
        Ophyd instance name of the detector used to center. This is only needed
        if the scan had more than one hinted detector.
    """

    yield from _move_to_pos("min", positioner=positioner, detector=detector)
import inspect
import os
from collections import defaultdict
from collections.abc import Mapping
from collections.abc import Sequence
from itertools import zip_longest
from typing import Any
from typing import Callable
from typing import Optional
from typing import Union

from bluesky import plan_stubs as bps
from bluesky import preprocessors as bpp
from bluesky import utils
from bluesky.protocols import Movable
from bluesky.protocols import Readable
from bluesky.utils import CustomPlanMetadata
from bluesky.utils import MsgGenerator
from cycler import Cycler

#: Plan function that can be used for each shot in a detector acquisition involving no actuation
PerShot = Callable[[Sequence[Readable], Optional[bps.TakeReading]], MsgGenerator]

#: Plan function that can be used for each step in a scan
PerStep1D = Callable[
    [Sequence[Readable], Movable, Any, Optional[bps.TakeReading]],
    MsgGenerator,
]
PerStepND = Callable[
    [
        Sequence[Readable],
        Mapping[Movable, Any],
        dict[Movable, Any],
        Optional[bps.TakeReading],
    ],
    MsgGenerator,
]
PerStep = Union[PerStep1D, PerStepND]


def _check_detectors_type_input(detectors):
    if not isinstance(detectors, Sequence):
        raise TypeError(
            "The input argument must be either as a list or a tuple of Readable objects."
        )


def scan_nd(
    detectors: Sequence[Readable],
    cycler: Cycler,
    *,
    per_step: Optional[PerStep] = None,
    md: Optional[CustomPlanMetadata] = None,
) -> MsgGenerator[str]:
    """
    Scan over an arbitrary N-dimensional trajectory.

    Parameters
    ----------
    detectors : list or tuple
    cycler : Cycler
        cycler.Cycler object mapping movable interfaces to positions
    per_step : callable, optional
        hook for customizing action of inner loop (messages per step).
        See docstring of :func:`bluesky.plan_stubs.one_nd_step` (the default)
        for details.
    md : dict, optional
        metadata

    See Also
    --------
    :func:`bluesky.plans.inner_product_scan`
    :func:`bluesky.plans.grid_scan`

    Examples
    --------
    >>> from cycler import cycler
    >>> cy = cycler(motor1, [1, 2, 3]) * cycler(motor2, [4, 5, 6])
    >>> scan_nd([sensor], cy)
    """
    _check_detectors_type_input(detectors)
    _md = {
        "detectors": [det.name for det in detectors],
        "motors": [motor.name for motor in cycler.keys],
        "num_points": len(cycler),
        "num_intervals": len(cycler) - 1,
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "cycler": repr(cycler),
            "per_step": repr(per_step),
        },
        "plan_name": "scan_nd",
        "hints": {},
    }
    _md.update(md or {})
    try:
        dimensions = [(motor.hints["fields"], "primary") for motor in cycler.keys]
    except (AttributeError, KeyError):
        # Not all motors provide a 'fields' hint, so we have to skip it.
        pass
    else:
        # We know that hints exists. Either:
        #  - the user passed it in and we are extending it
        #  - the user did not pass it in and we got the default {}
        # If the user supplied hints includes a dimension entry, do not
        # change it, else set it to the one generated above
        _md["hints"].setdefault("dimensions", dimensions)  # type: ignore

    predeclare = per_step is None and os.environ.get("BLUESKY_PREDECLARE", False)
    if per_step is None:
        per_step = bps.one_nd_step
    else:
        # Ensure that the user-defined per-step has the expected signature.
        sig = inspect.signature(per_step)

        def _verify_1d_step(sig):
            if len(sig.parameters) < 3:
                return False
            for name, (p_name, p) in zip_longest(
                ["detectors", "motor", "step"], sig.parameters.items()
            ):
                # this is one of the first 3 positional arguements, check that the name matches
                if name is not None:
                    if name != p_name:
                        return False
                # if there are any extra arguments, check that they have a default
                else:
                    if p.kind is p.VAR_KEYWORD or p.kind is p.VAR_POSITIONAL:
                        continue
                    if p.default is p.empty:
                        return False

            return True

        def _verify_nd_step(sig):
            if len(sig.parameters) < 3:
                return False
            for name, (p_name, p) in zip_longest(
                ["detectors", "step", "pos_cache"], sig.parameters.items()
            ):
                # this is one of the first 3 positional arguements, check that the name matches
                if name is not None:
                    if name != p_name:
                        return False
                # if there are any extra arguments, check that they have a default
                else:
                    if p.kind is p.VAR_KEYWORD or p.kind is p.VAR_POSITIONAL:
                        continue
                    if p.default is p.empty:
                        return False

            return True

        if sig == inspect.signature(bps.one_nd_step):
            pass
        elif _verify_nd_step(sig):
            # check other signature for back-compatibility
            pass
        elif _verify_1d_step(sig):
            # Accept this signature for back-compat reasons (because
            # inner_product_scan was renamed scan).
            dims = len(list(cycler.keys))
            if dims != 1:
                raise TypeError(
                    f"Signature of per_step assumes 1D trajectory but {dims} motors are specified."
                )
            (motor,) = cycler.keys
            user_per_step = per_step

            def adapter(detectors, step, pos_cache):
                # one_nd_step 'step' parameter is a dict; one_id_step 'step'
                # parameter is a value
                (step,) = step.values()
                return (yield from user_per_step(detectors, motor, step))

            per_step = adapter  # type: ignore
        else:
            raise TypeError(
                "per_step must be a callable with the signature \n "
                "<Signature (detectors, step, pos_cache)> or "
                "<Signature (detectors, motor, step)>. \n"
                f"per_step signature received: {sig}"
            )
    pos_cache: dict = defaultdict(lambda: None)  # where last position is stashed
    cycler = utils.merge_cycler(cycler)
    motors = list(cycler.keys)

    @bpp.stage_decorator(list(detectors) + motors)
    @bpp.run_decorator(md=_md)
    def inner_scan_nd():
        if predeclare:
            yield from bps.declare_stream(*motors, *detectors, name="primary")
        for step in list(cycler):
            yield from per_step(detectors, step, pos_cache)

    return (yield from inner_scan_nd())

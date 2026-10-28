"""S2IDD-specific Blop acquisition behavior."""

from collections.abc import Mapping, Sequence
from typing import Any

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from blop.plans import default_acquire


def s2idd_blop_acquire(
    suggestions: Sequence[Mapping[str, Any]],
    actuators: Sequence[Any],
    sensors: Sequence[Any] | None = None,
    md: Mapping[str, Any] | None = None,
    *,
    settle_time: float = 0.1,
    move_order: Sequence[Any] | None = None,
    extra_readables: Sequence[Any] | None = None,
    baseline_readables: Sequence[Any] | None = None,
    **kwargs: Any,
):
    """Acquire suggestions with ordered motor motion and scaler reads."""
    sensors = list(sensors or [])
    actuators = list(actuators)
    extra_readables = list(extra_readables or [])
    ordered_actuators = actuators if move_order is None else list(move_order)
    if set(ordered_actuators) != set(actuators):
        raise ValueError("move_order must contain each actuator exactly once")

    def per_step(detectors, step, pos_cache):
        del pos_cache
        for actuator in ordered_actuators:
            try:
                value = step[actuator]
            except KeyError as exc:
                raise KeyError(
                    f"Blop suggestion is missing actuator {actuator.name!r}"
                ) from exc
            yield from bps.mv(actuator, value)

        if settle_time > 0:
            yield from bps.sleep(settle_time)
        yield from bps.trigger_and_read(
            [*detectors, *actuators, *extra_readables],
            name="primary",
        )

    if baseline_readables:
        acquisition = default_acquire(
            suggestions,
            actuators,
            sensors,
            per_step=per_step,
            **kwargs,
        )
        return (
            yield from bpp.baseline_wrapper(
                acquisition,
                list(baseline_readables),
            )
        )

    return (
        yield from default_acquire(
            suggestions,
            actuators,
            sensors,
            per_step=per_step,
            **kwargs,
        )
    )

"""QueueServer worker operations for the staged M1 mirror alignment.

All device access takes place in the initialized beamline worker.  The skill's
uv client sends only JSON-compatible parameters and receives simple results.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import oregistry


_coarse_agent = None
_fine_agent = None


def _finite(value: float, name: str, *, positive: bool = False) -> float:
    value = float(value)
    if not math.isfinite(value) or (positive and value <= 0):
        raise ValueError(f"{name} must be finite" + (" and positive" if positive else ""))
    return value


def _summary(agent) -> dict:
    return {
        "name": agent.blop_name,
        "bounds": {name: list(bound) for name, bound in agent.bounds.items()},
        "step_sizes": dict(agent.step_sizes),
        "objectives": list(agent.objective_names),
    }


def _positive_integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _best_result(agent, objective: str, iterations: int, n_points: int) -> dict:
    """Serialize the best measured trial for QueueServer's JSON response."""
    points = agent.get_best_points()
    if not points:
        raise ValueError(f"{agent.blop_name} has no completed trials")

    def measured_value(point):
        value = point[2][objective]
        return float(value[0] if isinstance(value, tuple) else value)

    best_point = max(points, key=measured_value)
    trial_index, parameters, _ = best_point
    actuator_names = {
        actuator.name for actuator in agent.to_optimization_problem().actuators
    }
    positions = {
        name: float(value)
        for name, value in parameters.items()
        if name in actuator_names
    }
    if set(positions) != actuator_names or not all(map(math.isfinite, positions.values())):
        raise ValueError("Best trial does not contain finite positions for every actuator")
    best_value = measured_value(best_point)
    if not math.isfinite(best_value):
        raise ValueError("Best trial has a non-finite objective value")
    return {
        "agent": agent.blop_name,
        "objective": objective,
        "best_value": best_value,
        "trial_index": int(trial_index),
        "axes": list(positions),
        "best_positions": positions,
        "iterations": iterations,
        "n_points": n_points,
        "points_requested": iterations * n_points,
    }


def prepare_beam_path(
    pinhole_y_out: float = 23.2,
    osa_y_out: float = 3.0,
    settle_time: float = 1.0,
):
    """Move only upstream pinhole Y and OSA Y out of the beam path."""
    pinhole = oregistry["upstream_pinhole"].y
    osa = oregistry["osa"].y
    pinhole_y_out = _finite(pinhole_y_out, "pinhole_y_out")
    osa_y_out = _finite(osa_y_out, "osa_y_out")
    settle_time = _finite(settle_time, "settle_time")
    if settle_time < 0:
        raise ValueError("settle_time must be nonnegative")
    pinhole.check_value(pinhole_y_out)
    osa.check_value(osa_y_out)
    yield from bps.mv(pinhole, pinhole_y_out, osa, osa_y_out)
    if settle_time:
        yield from bps.sleep(settle_time)
    return {"upstream_pinhole_y": float(pinhole.position), "osa_y": float(osa.position)}


def put_pinhole_in(pinhole_y_in: float = 18.2, settle_time: float = 1.0):
    """Move only upstream pinhole Y into the beam path."""
    pinhole = oregistry["upstream_pinhole"].y
    pinhole_y_in = _finite(pinhole_y_in, "pinhole_y_in")
    settle_time = _finite(settle_time, "settle_time")
    if settle_time < 0:
        raise ValueError("settle_time must be nonnegative")
    pinhole.check_value(pinhole_y_in)
    yield from bps.mv(pinhole, pinhole_y_in)
    if settle_time:
        yield from bps.sleep(settle_time)
    return {"upstream_pinhole_y": float(pinhole.position)}


def read_alignment_state() -> dict:
    """Read current motor positions and the most recent scaler values."""
    scaler = oregistry["joerger_scaler"]
    return {
        "upstream_pinhole_y": float(oregistry["upstream_pinhole"].y.position),
        "osa_y": float(oregistry["osa"].y.position),
        "m1mirror_pitch": float(oregistry["m1mirror"].pitch.position),
        "mono_motors_pitch": float(oregistry["mono_motors"].pitch.position),
        "usic_counts": float(scaler.usic_counts.get()),
        "dsic_counts": float(scaler.dsic_counts.get()),
    }


def create_coarse_agent(
    ranges: Mapping[str, float] | None = None,
    step_sizes: Mapping[str, float] | None = None,
    count_time: float = 1.0,
    settle_time: float = 1.0,
    objective: str = "usic_counts",
):
    """Create a fresh M1 agent centered on the current mirror position."""
    global _coarse_agent, _fine_agent
    from s2idd_auto.blop.agents import make_coarse_agent

    ranges = dict(ranges or {"m1mirror_pitch": 0.02})
    if set(ranges) != {"m1mirror_pitch"}:
        raise ValueError("The coarse agent must optimize only m1mirror_pitch")
    if objective != "usic_counts":
        raise ValueError("The coarse objective must be usic_counts")
    _coarse_agent = make_coarse_agent(
        ranges=ranges,
        step_sizes=dict(step_sizes or {"m1mirror_pitch": 0.001}),
        count_time=_finite(count_time, "count_time", positive=True),
        settle_time=_finite(settle_time, "settle_time"),
        objective=objective,
        checkpoint_path=None,
    )
    _fine_agent = None
    return _summary(_coarse_agent)


def run_coarse_optimization(
    iterations: int = 1,
    n_points: int = 5,
    comment: str = "M1 coarse optimization with USIC objective",
):
    """Optimize M1, restore its start, and return the best measured position."""
    if _coarse_agent is None:
        raise RuntimeError("Call create_coarse_agent first")
    iterations = _positive_integer(iterations, "iterations")
    n_points = _positive_integer(n_points, "n_points")
    from s2idd_auto.blop.plans import run_blop_optimization

    yield from run_blop_optimization(
        _coarse_agent,
        iterations=iterations,
        n_points=n_points,
        objective_name="usic_counts",
        comment=comment,
    )
    return _best_result(_coarse_agent, "usic_counts", iterations, n_points)


def move_coarse_best(objective: str = "usic_counts"):
    """Move M1 to the best completed coarse-agent position."""
    if _coarse_agent is None:
        raise RuntimeError("Call create_coarse_agent first")
    from s2idd_auto.blop.plans import move_to_best_position

    return (yield from move_to_best_position(_coarse_agent, objective=objective))


def create_fine_agent(
    ranges: Mapping[str, float] | None = None,
    step_sizes: Mapping[str, float] | None = None,
    count_time: float = 1.0,
    settle_time: float = 1.0,
    objective: str = "dsic_counts",
):
    """Create an M1/mono-pitch agent seeded by completed coarse USIC trials."""
    global _fine_agent
    if _coarse_agent is None:
        raise RuntimeError("Run a coarse agent before creating the fine agent")
    from s2idd_auto.blop.agents import make_fine_agent

    ranges = dict(ranges or {"m1mirror_pitch": 0.001, "mono_motors_pitch": 0.002})
    if set(ranges) != {"m1mirror_pitch", "mono_motors_pitch"}:
        raise ValueError("The fine agent must optimize M1 pitch and mono pitch")
    if objective != "dsic_counts":
        raise ValueError("The fine objective must be dsic_counts")
    _fine_agent = make_fine_agent(
        coarse_agent=_coarse_agent,
        seed_objective="usic_counts",
        ranges=ranges,
        step_sizes=dict(step_sizes or {"m1mirror_pitch": 0.0002, "mono_motors_pitch": 0.0002}),
        count_time=_finite(count_time, "count_time", positive=True),
        settle_time=_finite(settle_time, "settle_time"),
        objective=objective,
        checkpoint_path=None,
    )
    return _summary(_fine_agent)


def run_fine_optimization(
    iterations: int = 10,
    n_points: int = 2,
    comment: str = "M1 and mono pitch fine optimization with DSIC objective",
):
    """Optimize M1/mono, restore their starts, and return the best positions."""
    if _fine_agent is None:
        raise RuntimeError("Call create_fine_agent first")
    iterations = _positive_integer(iterations, "iterations")
    n_points = _positive_integer(n_points, "n_points")
    from s2idd_auto.blop.plans import run_blop_optimization

    yield from run_blop_optimization(
        _fine_agent,
        iterations=iterations,
        n_points=n_points,
        objective_name="dsic_counts",
        comment=comment,
    )
    return _best_result(_fine_agent, "dsic_counts", iterations, n_points)


def move_to_alignment_positions(
    positions: Mapping[str, float],
    settle_time: float = 1.0,
):
    """Move only the optics axes named in a serialized optimization result."""
    axes = {
        "m1mirror_pitch": oregistry["m1mirror"].pitch,
        "mono_motors_pitch": oregistry["mono_motors"].pitch,
    }
    positions = dict(positions)
    if not positions or set(positions) - set(axes):
        raise ValueError("positions must contain only m1mirror_pitch and/or mono_motors_pitch")
    settle_time = _finite(settle_time, "settle_time")
    if settle_time < 0:
        raise ValueError("settle_time must be nonnegative")
    targets = {
        name: _finite(positions[name], name)
        for name in axes
        if name in positions
    }
    for name, value in targets.items():
        axes[name].check_value(value)
    for name, value in targets.items():
        yield from bps.mv(axes[name], value)
    if settle_time:
        yield from bps.sleep(settle_time)
    return {name: float(axes[name].position) for name in targets}


def move_alignment_to_best(objective: str = "dsic_counts"):
    """Move M1 and mono pitch to the best completed fine-agent position."""
    if _fine_agent is None:
        raise RuntimeError("Call create_fine_agent first")
    from s2idd_auto.blop.plans import move_to_best_position

    return (yield from move_to_best_position(_fine_agent, objective=objective))


def normalize_preamps(
    saturation_counts: float = 900000.0,
    target_counts: float = 400000.0,
    tolerance_counts: float = 100000.0,
):
    """Measure both channels and reduce saturated SR570 gains toward target."""
    saturation = _finite(saturation_counts, "saturation_counts", positive=True)
    target = _finite(target_counts, "target_counts", positive=True)
    tolerance = _finite(tolerance_counts, "tolerance_counts", positive=True)
    scaler = oregistry["joerger_scaler"]
    preamps = oregistry["preamps"]
    gain_factors = {0: 1, 2: 2, 3: 10, 4: 20, 5: 50, 6: 100, 7: 200, 8: 500}
    unit_factors = {0: 0.001, 1: 1, 2: 1000, 3: 1_000_000}
    levels = sorted(
        (unit * gain, unit_code, gain_code)
        for unit_code, unit in unit_factors.items()
        for gain_code, gain in gain_factors.items()
    )
    @bpp.run_decorator(md={"plan_name": "normalize_preamps"})
    def _measure_and_adjust():
        readings = yield from bps.trigger_and_read([scaler])
        counts = {
            "upstream": float(readings[scaler.usic_counts.name]["value"]),
            "downstream": float(readings[scaler.dsic_counts.name]["value"]),
        }
        changes = {}
        for side, count in counts.items():
            if count <= saturation:
                continue
            preamp = getattr(preamps, side)
            old_unit = int(preamp.gain_unit.get())
            old_gain = int(preamp.gain_value.get())
            current = unit_factors[old_unit] * gain_factors[old_gain]
            # SR570 settings are current per volt: a *larger* sensitivity
            # setting yields fewer counts at the same incident current.
            desired = current * count / target
            higher = [level for level in levels if level[0] >= desired]
            _, new_unit, new_gain = higher[0] if higher else levels[-1]
            if (new_unit, new_gain) == (old_unit, old_gain):
                continue
            yield from bps.mv(preamp.gain_unit, new_unit, preamp.gain_value, new_gain)
            changes[side] = {
                "old_unit": old_unit, "old_gain": old_gain,
                "new_unit": new_unit, "new_gain": new_gain,
            }
        return {
            "counts": counts,
            "changes": changes,
            "target_range": [target - tolerance, target + tolerance],
        }

    return (yield from _measure_and_adjust())

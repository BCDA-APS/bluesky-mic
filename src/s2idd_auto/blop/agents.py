"""Standard S2IDD optics optimization agents."""

from collections.abc import Mapping, Sequence
from typing import Any

from apsbits.core.instrument_init import oregistry
from blop.ax import Agent
from blop.ax import Objective
from blop.ax import RangeDOF

from .acquire import s2idd_blop_acquire
from .evaluators import evaluate_scaler


class S2IDDAgent(Agent):
    """Agent with an in-place reset of its Ax optimization state."""

    def __init__(self, *args: Any, **kwargs: Any):
        # Keep the original construction recipe so refresh() can create a new
        # empty Ax experiment without changing the public agent object.
        self._s2idd_agent_args = args
        self._s2idd_agent_kwargs = dict(kwargs)
        super().__init__(*args, **kwargs)

    def refresh(self):
        """Clear completed trials and restart suggestions in the same agent.

        The search space, step sizes, objectives, devices, and acquisition
        plan are retained.  Only the internal Ax experiment/model state is
        replaced, so the next call to ``agent.optimize()`` starts fresh.
        """
        fresh = type(self)(
            *self._s2idd_agent_args,
            **self._s2idd_agent_kwargs,
        )

        # Preserve metadata added by this beamline wrapper and any user-added
        # attributes, while taking the new optimizer/callback state from the
        # fresh agent.
        internal = {
            "_optimizer",
            "_readable_cache",
            "_callbacks",
            "_callback_router",
        }
        metadata = {key: value for key, value in self.__dict__.items() if key not in internal}
        self.__dict__.update(fresh.__dict__)
        self.__dict__.update(metadata)
        return self


def make_s2idd_agent(
    *,
    actuators: Sequence[Any],
    bounds: Mapping[str, tuple[float, float]],
    step_sizes: Mapping[str, float] | None = None,
    evaluation_function,
    objectives: Sequence[Objective] | None = None,
    sensors: Sequence[Any] | None = None,
    checkpoint_path: str | None = "s2idd_blop_checkpoint.json",
    settle_time: float = 0.1,
    move_order: Sequence[Any] | None = None,
    extra_readables: Sequence[Any] | None = None,
    baseline_readables: Sequence[Any] | None = None,
    name: str = "s2idd-beam-optimization",
    **kwargs: Any,
):
    """Create a Blop Agent after validating explicit motor boundaries."""
    actuators = list(actuators)
    step_sizes = dict(step_sizes or {})
    missing = [actuator.name for actuator in actuators if actuator.name not in bounds]
    if missing:
        raise ValueError(f"Missing safe Blop bounds for: {', '.join(missing)}")

    dofs = [
        RangeDOF(
            actuator=actuator,
            bounds=tuple(bounds[actuator.name]),
            parameter_type="float",
            step_size=step_sizes.get(actuator.name),
        )
        for actuator in actuators
    ]

    if objectives is None:
        objectives = [
            Objective(name="usic_counts", minimize=False),
            Objective(name="dsic_counts", minimize=False),
        ]

    def acquisition_plan(suggestions, plan_actuators, plan_sensors=None, md=None):
        return (
            yield from s2idd_blop_acquire(
                suggestions,
                plan_actuators,
                plan_sensors,
                md=md,
                settle_time=settle_time,
                move_order=move_order,
                extra_readables=extra_readables,
                baseline_readables=baseline_readables,
            )
        )

    agent = S2IDDAgent(
        sensors=list(sensors or []),
        dofs=dofs,
        objectives=list(objectives),
        evaluation_function=evaluation_function,
        acquisition_plan=acquisition_plan,
        checkpoint_path=checkpoint_path,
        name=name,
        **kwargs,
    )
    # Keep the optimization configuration directly inspectable.  Blop uses
    # the RangeDOF objects internally, but these mappings are more convenient
    # in an interactive beamline session.
    agent.bounds = {name: tuple(bounds[name]) for name in bounds}
    agent.step_sizes = {
        actuator.name: step_sizes.get(actuator.name)
        for actuator in actuators
    }
    # Singular aliases are retained as convenient interactive spellings.  For
    # multi-axis agents they are mappings, not scalar values.
    agent.stepsize = agent.step_sizes
    agent.range = agent.bounds
    return agent


COARSE_RANGES = {"m1mirror_pitch": 0.02}
FINE_RANGES = {
    "m1mirror_pitch": 0.001,
    "mono_motors_pitch": 0.002,
}

DEFAULT_STEPSIZES = {
    "m1mirror_pitch": 0.001,
    "mono_motors_bragg": 0.001,
    "mono_motors_pitch": 0.0002,
    "mono_motors_roll": 0.0005,
    "mono_motors_gap": 0.02,
}

MOVE_ORDER = (
    "m1mirror_pitch",
    "mono_motors_pitch",
    "mono_motors_bragg",
    "mono_motors_gap",
    "mono_motors_roll",
)


def _make_optics_agent(
    *,
    name: str,
    ranges: Mapping[str, float],
    step_sizes: Mapping[str, float] | None = None,
    count_time: float = 1.0,
    settle_time: float = 1.0,
    objective: str | Sequence[str] = "usic_counts",
    checkpoint_path: str | None,
    centers: Mapping[str, float] | None = None,
    **kwargs: Any,
):
    m1mirror = oregistry["m1mirror"]
    mono = oregistry["mono_motors"]
    scaler = oregistry["joerger_scaler"]
    preamps = oregistry["preamps"]
    kohzu_mono = oregistry["kohzu_mono"]
    upstream_pinhole = oregistry["upstream_pinhole"]

    available = {
        "m1mirror_pitch": m1mirror.pitch,
        "mono_motors_bragg": mono.bragg,
        "mono_motors_pitch": mono.pitch,
        "mono_motors_gap": mono.gap,
        "mono_motors_roll": mono.roll,
    }
    unknown = set(ranges) - set(available)
    if unknown:
        raise ValueError(f"Unknown optics axis/axes: {sorted(unknown)}")

    centers = dict(centers or {})
    unknown_centers = set(centers) - set(ranges)
    if unknown_centers:
        raise ValueError(
            f"Seed centers were provided for axes not in this agent: "
            f"{sorted(unknown_centers)}"
        )

    bounds = {}
    for name_, half_range in ranges.items():
        if half_range <= 0:
            raise ValueError(f"Relative range for {name_!r} must be positive")
        motor = available[name_]
        center = float(centers.get(name_, motor.position))
        bounds[name_] = (center - half_range, center + half_range)

    if count_time <= 0:
        raise ValueError("count_time must be greater than zero")
    scaler.count_time.put(count_time, wait=True)

    step_sizes = dict(step_sizes or {})
    for name_ in ranges:
        step_sizes.setdefault(name_, DEFAULT_STEPSIZES[name_])

    objective_names = [objective] if isinstance(objective, str) else list(objective)
    valid_objectives = {"usic_counts", "dsic_counts"}
    invalid = set(objective_names) - valid_objectives
    if invalid:
        raise ValueError(
            f"Unknown objective(s): {sorted(invalid)}. "
            f"Choose from {sorted(valid_objectives)}."
        )
    if not objective_names:
        raise ValueError("objective must contain at least one objective name")
    kwargs.setdefault(
        "objectives",
        [Objective(name=name_, minimize=False) for name_ in objective_names],
    )
    actuators = [available[name_] for name_ in ranges]
    move_order = [available[name_] for name_ in MOVE_ORDER if name_ in ranges]
    preamp_readables = [
        signal
        for preamp in (preamps.upstream, preamps.downstream)
        for signal in (
            preamp.gain_value,
            preamp.gain_unit,
            preamp.gain_mode,
            preamp.invert_mode,
            preamp.bias_mode,
        )
    ]
    extra_readables = [
        *preamp_readables,
        kohzu_mono,
        upstream_pinhole.x,
        upstream_pinhole.y,
    ]

    agent = make_s2idd_agent(
        actuators=actuators,
        bounds=bounds,
        step_sizes=step_sizes,
        sensors=[scaler],
        evaluation_function=evaluate_scaler,
        settle_time=settle_time,
        move_order=move_order,
        baseline_readables=extra_readables,
        checkpoint_path=checkpoint_path,
        name=name,
        **kwargs,
    )
    agent.blop_name = name
    agent.objective_names = list(objective_names)
    agent.baseline_readables = extra_readables
    # ``ranges`` are relative half-ranges used to construct the absolute
    # bounds around the positions observed at agent creation time.
    agent.ranges = dict(ranges)
    agent.range = agent.ranges
    agent.centers = {
        name_: float((lower + upper) / 2)
        for name_, (lower, upper) in bounds.items()
    }
    return agent


def make_coarse_agent(
    *,
    ranges: Mapping[str, float] | None = None,
    step_sizes: Mapping[str, float] | None = None,
    count_time: float = 1.0,
    settle_time: float = 1.0,
    objective: str | Sequence[str] = ("usic_counts", "dsic_counts"),
    checkpoint_path: str | None = "coarse_optics_blop_checkpoint.json",
    **kwargs: Any,
):
    """Make the coarse optics agent, optimizing only M1 pitch.

    ``ranges`` are relative half-ranges around the motor positions at agent
    creation time.  ``step_sizes`` are the maximum allowed spacing between
    candidate positions for each axis.
    """
    return _make_optics_agent(
        name="coarse-optics",
        ranges=COARSE_RANGES if ranges is None else ranges,
        step_sizes=step_sizes,
        count_time=count_time,
        settle_time=settle_time,
        objective=objective,
        checkpoint_path=checkpoint_path,
        **kwargs,
    )


def make_fine_agent(
    *,
    ranges: Mapping[str, float] | None = None,
    step_sizes: Mapping[str, float] | None = None,
    count_time: float = 1.0,
    settle_time: float = 1.0,
    objective: str | Sequence[str] = "usic_counts",
    checkpoint_path: str | None = "fine_optics_blop_checkpoint.json",
    coarse_agent=None,
    seed_objective: str = "usic_counts",
    **kwargs: Any,
):
    """Make the fine optics agent from a completed coarse agent."""
    centers = kwargs.pop("centers", None)
    if coarse_agent is None:
        raise ValueError(
            "make_fine_agent requires the completed coarse agent as coarse_agent"
        )
    if coarse_agent is not None:
        try:
            best_points = coarse_agent.get_best_points()
        except Exception as exc:
            raise ValueError(
                "coarse_agent does not contain completed optimization trials"
            ) from exc
        if not best_points:
            raise ValueError("coarse_agent has no best point to seed the fine agent")

        def objective_value(point):
            value = point[2][seed_objective]
            return value[0] if isinstance(value, tuple) else value

        try:
            best_point = max(best_points, key=objective_value)
            seed_parameters = best_point[1]
            seed_m1_pitch = float(seed_parameters["m1mirror_pitch"])
        except (KeyError, TypeError, IndexError) as exc:
            raise ValueError(
                f"Could not find {seed_objective!r} and m1mirror_pitch "
                "in the coarse agent's best point"
            ) from exc

        centers = dict(centers or {})
        centers["m1mirror_pitch"] = seed_m1_pitch

    return _make_optics_agent(
        name="fine-optics",
        ranges=FINE_RANGES if ranges is None else ranges,
        step_sizes=step_sizes,
        count_time=count_time,
        settle_time=settle_time,
        objective=objective,
        checkpoint_path=checkpoint_path,
        centers=centers,
        **kwargs,
    )


def refresh_agents(
    *,
    coarse_ranges: Mapping[str, float] | None = None,
    coarse_step_sizes: Mapping[str, float] | None = None,
    coarse_objective: str | Sequence[str] = ("usic_counts", "dsic_counts"),
    count_time: float = 1.0,
    settle_time: float = 1.0,
    fresh: bool = True,
    coarse_checkpoint_path: str | None = None,
):
    """Rebuild and return the startup-created coarse agent.

    The factories recenter their bounds on the current motor positions, so
    this is the convenient way to refresh the search windows after manually
    moving the optics.  By default, ``fresh=True`` creates new Ax experiments
    without reusing checkpoint files.  Set ``fresh=False`` to reuse the
    standard checkpoint files, or provide explicit checkpoint paths.
    """
    if not fresh:
        coarse_checkpoint_path = (
            "coarse_optics_blop_checkpoint.json"
            if coarse_checkpoint_path is None
            else coarse_checkpoint_path
        )

    return make_coarse_agent(
        ranges=coarse_ranges,
        step_sizes=coarse_step_sizes,
        count_time=count_time,
        settle_time=settle_time,
        objective=coarse_objective,
        checkpoint_path=coarse_checkpoint_path,
    )



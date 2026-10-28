"""Generic plans for running standard S2IDD Blop agents."""

from collections.abc import Mapping, Sequence
from typing import Any

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp

from apsbits.core.instrument_init import oregistry

from .plotting import save_agent_figures


def _capture_positions(agent):
    return {
        actuator.name: float(actuator.position)
        for actuator in agent.to_optimization_problem().actuators
    }


def _restore_positions(agent, positions):
    actuators = {
        actuator.name: actuator
        for actuator in agent.to_optimization_problem().actuators
    }
    for name, position in positions.items():
        yield from bps.mv(actuators[name], position)


def _best_parameters(agent, objective: str) -> dict[str, float]:
    """Return the parameters from the best completed agent trial."""
    try:
        best_points = agent.get_best_points()
    except Exception as exc:
        raise ValueError(
            f"Agent {getattr(agent, 'blop_name', agent)!r} has no completed trials"
        ) from exc
    if not best_points:
        raise ValueError(
            f"Agent {getattr(agent, 'blop_name', agent)!r} has no completed trials"
        )

    def objective_value(point):
        try:
            value = point[2][objective]
        except (IndexError, KeyError, TypeError) as exc:
            raise ValueError(
                f"Objective {objective!r} is not available in the agent results"
            ) from exc
        return value[0] if isinstance(value, tuple) else value

    best_point = max(best_points, key=objective_value)
    return {name: float(value) for name, value in best_point[1].items()}


def move_to_best_position(
    agent,
    *,
    objective: str = "usic_counts",
    settle_time: float = 1.0,
):
    """Move an agent's Ophyd actuators to its best completed positions.

    The best trial for ``objective`` is selected from ``agent``. Motors are
    moved in the agent's actuator order.
    """
    parameters = _best_parameters(agent, objective)

    actuators = {}
    for actuator in agent.to_optimization_problem().actuators:
        actuators[actuator.name] = actuator

    target_positions = dict(parameters)
    unknown = set(target_positions) - set(actuators)
    if unknown:
        raise ValueError(f"Best-point axes are not available: {sorted(unknown)}")

    ordered_names = [
        actuator.name
        for actuator in agent.to_optimization_problem().actuators
        if actuator.name in target_positions
    ]
    ordered_names = list(dict.fromkeys(ordered_names))
    for name in ordered_names:
        yield from bps.mv(actuators[name], target_positions[name])
    if settle_time > 0:
        yield from bps.sleep(settle_time)
    return target_positions


# Backward-compatible name for the optics-specific use case.
move_to_best_optics = move_to_best_position


def run_blop_optimization(
    agent,
    *,
    iterations: int = 5,
    n_points: int = 1,
    objective_name: str | Sequence[str] | None = None,
    comment: str | None = None,
    md: Mapping[str, Any] | None = None,
):
    """Optimize, restore positions, save plots, and annotate the run.

    ``comment`` is stored in the run's start-document metadata under the
    ``comment`` key. Additional metadata can be supplied through ``md``.
    """
    savedata = oregistry["savedata"]
    start_positions = _capture_positions(agent)
    run_md = dict(md or {})
    if comment is not None:
        run_md["comment"] = comment

    @bpp.run_decorator(md=run_md)
    def _run():
        next_number = savedata.next_scan_number.get()
        yield from savedata.set_next_scan_number(next_number + 1)
        savedata.update_next_file_name()

        try:
            yield from agent.optimize(iterations=iterations, n_points=n_points)
        finally:
            yield from _restore_positions(agent, start_positions)
            yield from bps.sleep(0.2)
            try:
                savedata.update_current_file_name()
                if objective_name is None:
                    objective_names = getattr(agent, "objective_names", ["usic_counts"])
                elif isinstance(objective_name, str):
                    objective_names = [objective_name]
                else:
                    objective_names = list(objective_name)

                figure_options = {}
                if getattr(agent, "blop_name", "") == "coarse-optics":
                    figure_options = {
                        "figsize": (14, 7),
                        "show_measurement_indices": False,
                    }
                paths = save_agent_figures(
                    agent,
                    savedata,
                    objective_names,
                    **figure_options,
                )
                for path in paths:
                    print(f"Blop figure saved to {path}")
            except Exception:
                import logging

                logging.getLogger(__name__).exception("Could not save Blop objective figure")

    yield from _run()

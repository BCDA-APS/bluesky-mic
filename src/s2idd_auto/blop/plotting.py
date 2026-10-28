"""Plotting and Ax-data helpers for S2IDD Blop optimizations."""

from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd


NATIVE_CONTOUR_CMAP = LinearSegmentedColormap.from_list(
    "s2idd_native",
    ["#b07b3f", "#d9c18e", "#f0ebcd", "#a7c0bd", "#2c8aa5"],
)
PLOT_AXIS_ORDER = (
    "m1mirror_pitch",
    "mono_motors_pitch",
    "mono_motors_bragg",
    "mono_motors_gap",
    "mono_motors_roll",
)


def _agent_name(agent) -> str:
    return (
        getattr(agent, "blop_name", None)
        or getattr(agent, "name", None)
        or getattr(getattr(agent, "_optimizer", None), "name", None)
        or "blop-agent"
    )


def _savedata_file_stem(savedata) -> str:
    """Get the current SaveData filename without its directory or suffix."""
    for attribute in ("current_file_name", "next_file_name"):
        filename = getattr(savedata, attribute, None)
        if filename:
            return Path(str(filename)).stem
    return "blop"


def _observed_objective_data(agent, axes: list[str], objective_name: str) -> pd.DataFrame:
    experiment = agent.ax_client._experiment
    measurements = experiment.fetch_data().df
    parameters = pd.DataFrame(
        [
            {"trial_index": trial_index, "arm_name": arm_name, **arm.parameters}
            for trial_index, trial in experiment.trials.items()
            for arm_name, arm in trial.arms_by_name.items()
        ]
    )
    if measurements.empty or parameters.empty:
        return pd.DataFrame()
    data = (
        measurements.pivot_table(
            index=["trial_index", "arm_name"],
            columns="metric_name",
            values="mean",
            aggfunc="first",
        )
        .reset_index()
        .merge(parameters, on=["trial_index", "arm_name"], how="left")
    )
    required = set(axes) | {objective_name}
    if not required.issubset(data.columns):
        return pd.DataFrame()
    return data.dropna(subset=list(required)).sort_values("trial_index")


def _one_dimensional_model_data(agent, axis_name: str, objective_name: str) -> pd.DataFrame:
    """Evaluate Ax's fitted surrogate on a 1-D grid, if available."""
    bounds = getattr(agent, "bounds", {}).get(axis_name)
    if bounds is None:
        return pd.DataFrame()
    lower, upper = map(float, bounds)
    step_size = getattr(agent, "step_sizes", {}).get(axis_name)
    if step_size:
        values = np.arange(lower, upper + abs(step_size) * 0.5, abs(step_size))
        values = values[values <= upper + abs(step_size) * 1e-6]
    else:
        values = np.linspace(lower, upper, 200)
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return pd.DataFrame()
    try:
        predictions = agent.ax_client.predict(
            [{axis_name: float(value)} for value in values]
        )
    except Exception:
        return pd.DataFrame()
    if not predictions or objective_name not in predictions[0]:
        return pd.DataFrame()
    means = np.asarray([prediction[objective_name][0] for prediction in predictions])
    standard_deviations = np.asarray(
        [prediction[objective_name][1] for prediction in predictions]
    )
    return pd.DataFrame(
        {
            axis_name: values,
            "mean": means,
            "lower": means - 2 * standard_deviations,
            "upper": means + 2 * standard_deviations,
        }
    )


def _axis_grid(agent, axis_name: str, max_points: int = 40) -> np.ndarray:
    """Build a prediction grid that respects a configured motor step size."""
    lower, upper = map(float, agent.bounds[axis_name])
    step_size = getattr(agent, "step_sizes", {}).get(axis_name)
    if step_size:
        values = np.arange(lower, upper + abs(step_size) * 0.5, abs(step_size))
        if len(values) > max_points:
            values = values[:: int(np.ceil(len(values) / max_points))]
        return values[values <= upper + abs(step_size) * 1e-6]
    return np.linspace(lower, upper, max_points)


def _two_dimensional_model_data(
    agent,
    x_axis: str,
    y_axis: str,
    objective_name: str,
) -> pd.DataFrame:
    """Evaluate Ax's fitted surrogate on a 2-D grid, if available."""
    if x_axis not in getattr(agent, "bounds", {}) or y_axis not in agent.bounds:
        return pd.DataFrame()

    x_values = _axis_grid(agent, x_axis)
    y_values = _axis_grid(agent, y_axis)
    xx, yy = np.meshgrid(x_values, y_values)
    centers = getattr(agent, "centers", {})
    fixed_point = {
        name: float(centers.get(name, sum(agent.bounds[name]) / 2))
        for name in agent.bounds
    }
    # Prefer coordinates from an actual completed arm. This avoids creating
    # invalid prediction points when Ax's discrete step grid does not include
    # the nominal center exactly.
    try:
        experiment = agent.ax_client._experiment
        for trial in experiment.trials.values():
            if trial.arms_by_name:
                arm = next(iter(trial.arms_by_name.values()))
                fixed_point.update(
                    {
                        name: float(value)
                        for name, value in arm.parameters.items()
                    }
                )
                break
    except Exception:
        pass
    # Ax requires a complete parameterization for prediction. For a 2-D
    # projection, hold every non-displayed motor at its configured center.
    points = []
    for x, y in zip(xx.ravel(), yy.ravel()):
        point = dict(fixed_point)
        point[x_axis] = float(x)
        point[y_axis] = float(y)
        points.append(point)
    try:
        predictions = agent.ax_client.predict(points)
    except Exception:
        return pd.DataFrame()
    if not predictions or objective_name not in predictions[0]:
        return pd.DataFrame()

    values = [prediction[objective_name] for prediction in predictions]
    return pd.DataFrame(
        {
            x_axis: xx.ravel(),
            y_axis: yy.ravel(),
            "mean": [value[0] for value in values],
            "std": [value[1] for value in values],
        }
    )


def _plot_observed_objective(
    data: pd.DataFrame,
    axes: list[str],
    objective_name: str,
    agent_name: str,
    model_data: pd.DataFrame | None = None,
    axis=None,
    model_color: str = "uncertainty",
    show_measurement_indices: bool = True,
):
    if axis is None:
        figure, axis = plt.subplots(figsize=(7, 5))
        owns_figure = True
    else:
        figure = axis.figure
        owns_figure = False

    best_index = data[objective_name].idxmax()
    best = data.loc[best_index]
    ordinary = data.index != best_index

    if len(axes) == 1:
        x_axis = axes[0]
        axis.scatter(data.loc[ordinary, x_axis], data.loc[ordinary, objective_name], color="cornflowerblue", label="Measured point", zorder=2)
        axis.scatter([best[x_axis]], [best[objective_name]], color="lightcoral", edgecolor="black", label="Best measured point", zorder=3)
        axis.set_xlabel(x_axis)
        axis.set_ylabel(objective_name)
        if model_data is not None and not model_data.empty:
            axis.plot(model_data[x_axis], model_data["mean"], color="navy", label="Model mean", zorder=1)
            axis.fill_between(model_data[x_axis], model_data["lower"], model_data["upper"], color="cornflowerblue", alpha=0.2, label="Model ±2σ", zorder=0)
    else:
        x_axis, y_axis = axes[:2]
        model_can_be_plotted = (
            model_data is not None
            and not model_data.empty
            and np.isfinite(model_data[["std", "mean"]].to_numpy()).all()
            and model_data[model_color].nunique() > 1
        )
        if model_can_be_plotted:
            contour_values = model_data[model_color]
            if model_color == "mean":
                contour_cmap = NATIVE_CONTOUR_CMAP
                colorbar_label = objective_name
            else:
                contour_cmap = "viridis"
                colorbar_label = "Model uncertainty (σ)"
            uncertainty = axis.tricontourf(
                model_data[x_axis],
                model_data[y_axis],
                contour_values,
                levels=12,
                cmap=contour_cmap,
                alpha=0.75,
                zorder=0,
            )
            axis.tricontour(
                model_data[x_axis],
                model_data[y_axis],
                model_data["mean"],
                levels=8,
                colors="white",
                linewidths=0.7,
                alpha=0.75,
                zorder=1,
            )
            axis.figure.colorbar(
                uncertainty,
                ax=axis,
                label=colorbar_label,
            )
        axis.scatter(data.loc[ordinary, x_axis], data.loc[ordinary, y_axis], color="cornflowerblue", label="Measured point", zorder=2)
        axis.scatter([best[x_axis]], [best[y_axis]], color="lightcoral", edgecolor="black", label=f"Best {objective_name}", zorder=3)
        axis.set_xlabel(x_axis)
        axis.set_ylabel(y_axis)

    if show_measurement_indices:
        for _, row in data.iterrows():
            label = str(int(row["trial_index"]))
            if row.name == best_index:
                label = f"{label}: {row[axes[0]]:.6g}"
            point = (row[axes[0]], row[objective_name]) if len(axes) == 1 else (row[axes[0]], row[axes[1]])
            axis.annotate(label, point, xytext=(4, 4), textcoords="offset points")

    # axis.set_title(f"{agent_name}: {objective_name}")
    axis.grid(True, alpha=0.3)
    # Legends are omitted to keep the multi-panel figure uncluttered.
    if owns_figure:
        figure.tight_layout()
    return figure


def save_agent_figures(
    agent,
    savedata,
    objective_names: Sequence[str],
    *,
    figsize: tuple[float, float] | None = None,
    show_measurement_indices: bool = True,
) -> list[Path]:
    """Save annotated objective subplots for the agent."""
    output_dir = Path(savedata.get_auto_storage_path()) / "blop"
    output_dir.mkdir(parents=True, exist_ok=True)
    agent_name = _agent_name(agent)
    file_stem = _savedata_file_stem(savedata)
    axes = [actuator.name for actuator in agent.to_optimization_problem().actuators]
    axes = sorted(
        axes,
        key=lambda name: (
            PLOT_AXIS_ORDER.index(name)
            if name in PLOT_AXIS_ORDER
            else len(PLOT_AXIS_ORDER)
        ),
    )
    paths = []

    if len(axes) >= 2:
        pairs = [
            (x_axis, y_axis)
            for index, x_axis in enumerate(axes[:-1])
            for y_axis in axes[index + 1 :]
        ]
        figure, subplot_axes = plt.subplots(
            len(objective_names),
            len(pairs),
            figsize=figsize or (7 * len(pairs), 5 * len(objective_names)),
            squeeze=False,
            sharex="col",
        )
        plotted = False
        for row_index, objective_name in enumerate(objective_names):
            for column_index, (x_axis, y_axis) in enumerate(pairs):
                data = _observed_objective_data(
                    agent, [x_axis, y_axis], objective_name
                )
                if data.empty:
                    continue
                model_data = _two_dimensional_model_data(
                    agent, x_axis, y_axis, objective_name
                )
                _plot_observed_objective(
                    data,
                    [x_axis, y_axis],
                    objective_name,
                    agent_name,
                    model_data=model_data,
                    axis=subplot_axes[row_index, column_index],
                    model_color="mean",
                    show_measurement_indices=show_measurement_indices,
                )
                plotted = True
        if not plotted:
            plt.close(figure)
            return paths
        figure.tight_layout()
        path = output_dir / f"{agent_name}_{file_stem}.png"
        figure.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(figure)
        paths.append(path)
    else:
        figure, subplot_axes = plt.subplots(
            1,
            len(objective_names),
            figsize=figsize or (7 * len(objective_names), 5),
            squeeze=False,
            sharex=True,
        )
        plotted = False
        for column_index, objective_name in enumerate(objective_names):
            data = _observed_objective_data(agent, axes, objective_name)
            if data.empty:
                continue
            model_data = _one_dimensional_model_data(agent, axes[0], objective_name)
            _plot_observed_objective(
                data,
                axes,
                objective_name,
                agent_name,
                model_data=model_data,
                axis=subplot_axes[0, column_index],
                show_measurement_indices=show_measurement_indices,
            )
            plotted = True
        if plotted:
            # figure.suptitle(agent_name)
            figure.tight_layout()
            path = output_dir / f"{agent_name}_{file_stem}.png"
            figure.savefig(path, dpi=150, bbox_inches="tight")
            plt.close(figure)
            paths.append(path)
        else:
            plt.close(figure)
    return paths


def save_native_objective_figures(
    agent,
    savedata,
    objective_names: Sequence[str],
) -> list[Path]:
    """Save Blop's native ``Agent.plot_objective`` figures.

    A separate native figure is saved for every actuator pair and objective.
    These plots show Ax's own model-predicted objective surface. PNG export is
    attempted first; HTML is used as a fallback if Kaleido is unavailable.
    """
    output_dir = Path(savedata.get_auto_storage_path()) / "blop"
    output_dir.mkdir(parents=True, exist_ok=True)
    agent_name = _agent_name(agent)
    file_stem = _savedata_file_stem(savedata)
    axes = [actuator.name for actuator in agent.to_optimization_problem().actuators]
    paths = []
    figure_index = 0

    if len(axes) < 2:
        return paths

    for index, x_axis in enumerate(axes[:-1]):
        for y_axis in axes[index + 1 :]:
            for objective_name in objective_names:
                try:
                    cards = agent.plot_objective(
                        x_axis,
                        y_axis,
                        objective_name,
                        display=False,
                    )
                    figure = cards[0].get_figure()
                except Exception:
                    # The native Ax plot requires a fitted predictive model.
                    continue

                figure_index += 1
                suffix = "" if figure_index == 1 else f"_{figure_index}"
                path = output_dir / f"{agent_name}_{file_stem}_native{suffix}.png"
                try:
                    figure.write_image(str(path))
                except Exception:
                    path = output_dir / f"{agent_name}_{file_stem}_native{suffix}.html"
                    figure.write_html(str(path))
                paths.append(path)

    return paths

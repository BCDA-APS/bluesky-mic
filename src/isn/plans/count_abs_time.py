"""
Count plan with absolute wall-clock time on the x-axis.

Note: requires an interactive matplotlib backend (e.g. call ``plt.ion()`` or
use the ``%matplotlib widget`` / ``%matplotlib qt`` magic before running).

``count_abs_time`` is a plain function, not a generator. Calling it runs
``plt.subplots()`` immediately in the calling (main) thread and returns a
generator to pass to the RunEngine. This keeps all figure-creation calls
outside the RunEngine's callback thread.

.. autosummary::
    ~LiveAbsTimePlot
    ~count_abs_time
"""

import logging
from datetime import datetime

import matplotlib.dates as mdates  # also registers the datetime unit converter
import matplotlib.pyplot as plt
from bluesky import plans as bp
from bluesky import preprocessors as bpp
from bluesky.callbacks.core import CallbackBase

logger = logging.getLogger(__name__)


def _hinted_fields(detectors):
    """Return hinted signal names for a list of detectors, mirroring BEC."""
    fields = []
    for det in detectors:
        hints = getattr(det, "hints", {})
        det_fields = hints.get("fields", [])
        if det_fields:
            fields.extend(det_fields)
        else:
            logger.warning(
                "Device %r has no hinted fields; falling back to device name. "
                "Its signals may not appear in doc['data'] and the panel will "
                "remain empty.",
                det.name,
            )
            fields.append(det.name)
    return fields


class LiveAbsTimePlot(CallbackBase):
    """Live plot with one subplot per signal and absolute wall-clock time on x.

    Mirrors BestEffortCallback's panel-per-signal layout, but uses absolute
    wall-clock time (``%b %d  %H:%M``) on the shared x-axis instead of
    elapsed time.

    The figure must be created before instantiating this class and passed via
    *axes*. ``count_abs_time`` handles this automatically.

    Parameters
    ----------
    ys : list of str
        Signal names (fields) to plot, one panel each.
    axes : sequence of matplotlib.axes.Axes
        Pre-existing axes, one per entry in *ys* (must match length).
    """

    def __init__(self, ys, *, axes):
        super().__init__()
        self.ys = list(ys)
        axes = list(axes)
        if len(axes) != len(self.ys):
            raise ValueError(
                f"axes length ({len(axes)}) must match the number of "
                f"signals ({len(self.ys)})"
            )
        self._axes = {y: axes[i] for i, y in enumerate(self.ys)}
        self._fig = axes[0].figure
        self._xs = {y: [] for y in self.ys}
        self._ys = {y: [] for y in self.ys}
        self._lines = {}

    def _setup_panels(self, scan_id):
        """Clear panels and reapply formatting. Never creates figures."""
        for y, ax in self._axes.items():
            ax.clear()
            ax.set_ylabel(y)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d  %H:%M"))

        # tick_params sets a persistent axis property; unlike setp on
        # get_xticklabels(), it does not require tick artists to exist yet.
        for y in self.ys[:-1]:
            self._axes[y].tick_params(labelbottom=False)

        bottom_ax = self._axes[self.ys[-1]]
        bottom_ax.set_xlabel("Time")
        bottom_ax.tick_params(axis="x", labelrotation=30)
        self._fig.suptitle(f"scan_id={scan_id}")

    def start(self, doc):
        super().start(doc)
        for buf in self._xs.values():
            buf.clear()
        for buf in self._ys.values():
            buf.clear()
        self._lines.clear()
        self._setup_panels(doc.get("scan_id", "?"))
        self._fig.canvas.draw_idle()

    def event(self, doc):
        super().event(doc)
        data = doc["data"]
        present = [y for y in self.ys if y in data]
        if not present:
            return

        t = datetime.fromtimestamp(doc["time"])

        for y in present:
            ax = self._axes[y]
            self._xs[y].append(t)
            self._ys[y].append(data[y])
            if y not in self._lines:
                (self._lines[y],) = ax.plot(self._xs[y], self._ys[y], "o-")
            else:
                self._lines[y].set_xdata(self._xs[y])
                self._lines[y].set_ydata(self._ys[y])
            ax.relim()
            ax.autoscale_view()

        # draw_idle() posts a repaint event to the GUI queue; thread-safe.
        self._fig.canvas.draw_idle()

    def stop(self, doc):
        super().stop(doc)
        self._fig.canvas.draw_idle()


def _count_abs_time_plan(detectors, num, delay, ys, axes, md):
    """Private generator that the RunEngine executes."""
    cb = LiveAbsTimePlot(ys, axes=axes)
    yield from bpp.subs_wrapper(
        bp.count(detectors, num=num, delay=delay, md=md),
        cb,
    )


def count_abs_time(detectors, num=1, delay=None, *, y=None, axes=None, md=None):
    """Run bp.count() with one live subplot per signal and absolute time on x.

    This is a **plain function**, not a generator. Calling it creates the
    figure immediately in the calling thread (the IPython main thread), then
    returns a generator to pass to the RunEngine. This prevents matplotlib
    from being called from the RunEngine's callback thread.

    Usage::

        RE(count_abs_time([det1, det2], num=60, delay=1))

    Parameters
    ----------
    detectors : list
        Detectors to read, same as bp.count().
    num : int
        Number of readings.
    delay : float or list of float, optional
        Delay between readings (seconds).
    y : str or list of str, optional
        Signal name(s) to plot. Defaults to the hinted fields of all detectors.
    axes : sequence of matplotlib.axes.Axes, optional
        Pre-existing axes, one per signal (must match signal count).
        A new figure is created here (in the calling thread) if omitted.
    md : dict, optional
        Extra metadata.

    Returns
    -------
    generator
        A bluesky plan generator to pass to the RunEngine.
    """
    if y is None:
        ys = _hinted_fields(detectors)
    elif isinstance(y, str):
        ys = [y]
    else:
        ys = list(y)

    if axes is None:
        # Figure is created here — in the calling (main) thread — before the
        # generator is handed to the RunEngine.
        n = len(ys)
        fig, axs = plt.subplots(
            n, 1, sharex=True, squeeze=False, figsize=(8, 3 * n)
        )
        plt.show(block=False)
        plt.pause(0.001)  # flush the event loop so the window appears
        axes = [axs[i, 0] for i in range(n)]
    else:
        axes = list(axes)
        if len(axes) != len(ys):
            raise ValueError(
                f"axes length ({len(axes)}) must match the number of "
                f"signals ({len(ys)})"
            )

    return _count_abs_time_plan(detectors, num, delay, ys, axes, md)

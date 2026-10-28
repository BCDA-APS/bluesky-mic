"""One-shot downstream ion chamber measurements with the Joerger scaler."""

import logging
import math

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from apsbits.core.instrument_init import oregistry

logger = logging.getLogger(__name__)


def read_dsic_counts(count_time: float = 1.0, *, md: dict | None = None):
    """Acquire one fresh DSIC reading, recording one primary event.

    Parameters
    ----------
    count_time : float
        Positive, finite scaler integration time in seconds.
    md : dict, optional
        Additional run metadata.

    Returns
    -------
    float
        Downstream ion chamber counts. The value is also logged and saved as
        ``joerger_scaler_dsic_counts`` in the run's primary stream.

    Examples
    --------
    >>> RE(read_dsic_counts(count_time=1.0))

    The scaler's trigger selects one-shot mode and waits for the preset time
    plus its settling margin before reading. This leaves the scaler in
    one-shot mode with the requested integration time.
    """
    count_time = float(count_time)
    if not math.isfinite(count_time) or count_time <= 0:
        raise ValueError("count_time must be a positive, finite number of seconds")

    scaler = oregistry["joerger_scaler"]
    metadata = dict(md or {})
    metadata.update(plan_name="read_dsic_counts", count_time=count_time)
    reading = {}

    @bpp.stage_decorator([scaler])
    @bpp.run_decorator(md=metadata)
    def acquire():
        yield from bps.mv(scaler.count_time, count_time)
        # Trigger the parent device: triggering the read-only DSIC signal
        # alone would only read the previous acquisition's value.
        reading.update((yield from bps.trigger_and_read([scaler])))

    yield from acquire()
    counts = float(reading[scaler.dsic_counts.name]["value"])
    logger.info("DSIC counts: %s (integration time: %s s)", counts, count_time)
    return counts

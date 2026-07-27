"""
Plans for moving KB mirror axes with automatic sample-position correction.

Coupling map (kb.py / sample.py):
    kb.x                        -> sample.x  (EpicsMotor, .user_readback.get())
    kb.theta_y                  -> sample.x  (EpicsMotor, .user_readback.get())
    kb.vertical_angle           -> sample.y  (EpicsSignalRO, .get())
    kb.vertical_average         -> sample.y  (EpicsSignalRO, .get())
    kb.coarse_vertical_angle_um -> sample.y  (VerticalKBAxis, .position)
    kb.fine_vertical_angle_um   -> sample.y  (VerticalKBAxis, .position)
    kb.coarse_y                 -> sample.y  (VerticalKBAxis, .position)
    kb.fine_y                   -> sample.y  (VerticalKBAxis, .position)

All other KB axes (y_ds, y_us, z, theta_z) pass through without any sample
correction.

For both mv_kb (absolute) and mvr_kb (relative), the sample correction is
always a bps.mvr computed from (post_rbv - pre_rbv) on each moved KB axis,
so backlash and limit truncation are automatically accounted for.

Usage
-----
    # Absolute KB move with sample correction:
    yield from mv_kb(kb.x, 5.0)
    yield from mv_kb(kb.theta_y, 0.2, kb.vertical_angle, -0.05)

    # Relative KB move with sample correction:
    yield from mvr_kb(kb.x, 0.1)
    yield from mvr_kb(kb.theta_y, -0.05, kb.vertical_average, 0.02)
    yield from mvr_kb(kb.coarse_vertical_angle_um, 1.0)
    yield from mvr_kb(kb.fine_vertical_angle_um, 0.5)

    # Move without sample correction (alignment mode):
    yield from mv_kb(kb.x, 5.0, correct=False)

    # Update calibrated coefficients after alignment:
    set_kb_correction(x_to_x=-1.23, theta_y_to_x=0.87)
    set_kb_correction(coarse_vertical_angle_um_to_y=2.1, fine_vertical_angle_um_to_y=2.0)
"""

import logging

import bluesky.plan_stubs as bps
from apsbits.core.instrument_init import oregistry

logger = logging.getLogger(__name__)

kb = oregistry["kb"]
sample = oregistry["sample"]

# ---------------------------------------------------------------------------
# Coupling coefficients
#
# Format: {kb_attr_name: (sample_attr_name, coefficient)}
# Units:  [sample EGU] / [KB EGU]
#
# All set to 0.0 until measured.  Update with set_kb_correction() after
# running an alignment scan.
# ---------------------------------------------------------------------------
KB_SAMPLE_COEFFICIENTS: dict[str, tuple[str, float]] = {
    "x":                          ("x", 0.001),
    "theta_y":                    ("x", 0.0),
    "theta_y.coarse":             ("x", 0.0015797),
    "theta_y.fine":               ("x", 0.0015797),
    "vertical_angle":             ("y", 0.0),
    "vertical_average":           ("y", 0.0),
    "coarse_vertical_angle_um":   ("y", 0.00586),
    "fine_vertical_angle_um":     ("y", 0.00586),
    "coarse_y":                   ("y", 0.001),
    "fine_y":                     ("y", 0.001),
}

_COUPLED_KB_AXES: frozenset[str] = frozenset(KB_SAMPLE_COEFFICIENTS.keys())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_kb_rbv(axis) -> float:
    """Read current position of a KB axis.

    Three axis types exist in the coupling map:
    - EpicsMotor subclasses (x, theta_y): expose .user_readback
    - EpicsSignalRO (vertical_angle, vertical_average): use .get()
    - VerticalAngleAxis (coarse/fine_vertical_angle_um): virtual device
      with no EPICS readback; use .position which tracks cumulative deltas
    """
    if hasattr(axis, "user_readback"):
        return axis.user_readback.get()
    if hasattr(axis, "_position"):
        return axis._position
    if hasattr(axis, "get"):
        return axis.get()
    return axis.position


def _parse_pairs(args):
    if len(args) % 2 != 0:
        raise ValueError(
            f"Expected an even number of (axis, value) arguments, got {len(args)}."
        )
    return [(args[i], args[i + 1]) for i in range(0, len(args), 2)]


def _resolve_attr_names(pairs) -> list[str]:
    """Map each axis object to its dotted attribute path on kb.

    Coupled axes (KB_SAMPLE_COEFFICIENTS keys, may be dotted e.g. 'theta_y.coarse')
    are searched first; uncoupled top-level components follow so that axes like
    kb.y_ds and kb.z are still accepted without triggering a correction.
    """
    all_paths = list(KB_SAMPLE_COEFFICIENTS.keys()) + [
        attr for attr in kb.component_names
        if attr not in KB_SAMPLE_COEFFICIENTS
    ]
    attr_names = []
    for axis, _ in pairs:
        matched = next(
            (path for path in all_paths if getattr(kb, path, None) is axis),
            None,
        )
        if matched is None:
            raise ValueError(
                f"{axis!r} is not a recognised KB axis. "
                f"Valid axes: {all_paths}"
            )
        attr_names.append(matched)
    return attr_names


def _compute_sample_corrections(attr_names, pre_rbvs, post_rbvs) -> dict[str, float]:
    """Sum KB-induced sample deltas across all coupled axes.

    kb.x and kb.theta_y both feed sample.x — their contributions are summed
    so a single bps.mvr corrects the sample.
    """
    sample_deltas: dict[str, float] = {}
    for attr, pre, post in zip(attr_names, pre_rbvs, post_rbvs):
        if attr not in _COUPLED_KB_AXES:
            continue
        sample_attr, coeff = KB_SAMPLE_COEFFICIENTS[attr]
        delta_kb = post - pre
        sample_deltas[sample_attr] = sample_deltas.get(sample_attr, 0.0) + coeff * delta_kb
    return sample_deltas


# ---------------------------------------------------------------------------
# Shared move engine
# ---------------------------------------------------------------------------

def _kb_move_with_correction(pairs, attr_names, kb_move_stub, correct):
    """Core generator used by both mv_kb and mvr_kb.

    kb_move_stub : bps.mv  (absolute) or bps.mvr (relative)
    correct      : if False, skip the sample correction entirely
    """
    # 1. Snapshot KB positions before the move
    pre_rbvs = [_get_kb_rbv(axis) for axis, _ in pairs]

    # 2. Issue the KB move (absolute or relative depending on stub)
    flat_kb_args = [item for axis, value in pairs for item in (axis, value)]
    yield from kb_move_stub(*flat_kb_args)

    if not correct:
        return

    # 3. Snapshot after — bps.mv/mvr block until DMOV so backlash is settled
    post_rbvs = [_get_kb_rbv(axis) for axis, _ in pairs]

    # 4. Compute net sample corrections
    sample_deltas = _compute_sample_corrections(attr_names, pre_rbvs, post_rbvs)
    if not sample_deltas:
        return

    logger.debug("mv_kb sample correction: %s", sample_deltas)

    # 5. Apply as a single simultaneous relative sample move
    flat_sample_args = [
        item
        for sample_attr, delta in sample_deltas.items()
        for item in (getattr(sample, sample_attr), delta)
    ]
    yield from bps.mvr(*flat_sample_args)


# ---------------------------------------------------------------------------
# Public plans
# ---------------------------------------------------------------------------

def mv_kb(*args, correct: bool = True):
    """Move KB axes to absolute positions and apply a relative sample correction.

    Parameters
    ----------
    *args : alternating (kb_axis, absolute_position) pairs, same as bps.mv.
    correct : bool
        True  — apply sample correction after the KB move (default).
        False — move KB only; skip correction (use during alignment scans).

    Examples
    --------
        yield from mv_kb(kb.x, 5.0)
        yield from mv_kb(kb.theta_y, 0.2, kb.vertical_angle, -0.05)
        yield from mv_kb(kb.x, 5.0, correct=False)
    """
    pairs = _parse_pairs(args)
    attr_names = _resolve_attr_names(pairs)
    yield from _kb_move_with_correction(pairs, attr_names, bps.mv, correct)


def mvr_kb(*args, correct: bool = True):
    """Move KB axes by relative amounts and apply a relative sample correction.

    The sample correction uses the actual achieved delta (post_rbv - pre_rbv),
    not the requested step, so soft-limit clipping and backlash are accounted
    for automatically.

    Parameters
    ----------
    *args : alternating (kb_axis, relative_step) pairs, same as bps.mvr.
    correct : bool
        True  — apply sample correction after the KB move (default).
        False — move KB only; skip correction.

    Examples
    --------
        yield from mvr_kb(kb.x, 0.1)
        yield from mvr_kb(kb.theta_y, -0.05, kb.vertical_average, 0.02)
    """
    pairs = _parse_pairs(args)
    attr_names = _resolve_attr_names(pairs)
    yield from _kb_move_with_correction(pairs, attr_names, bps.mvr, correct)


# ---------------------------------------------------------------------------
# Coefficient management (not a plan)
# ---------------------------------------------------------------------------

def set_kb_correction(coefficients: dict = None, **kwargs) -> dict:
    """Update KB-to-sample coupling coefficients in-place.

    Coefficient names follow the pattern <kb_attr>_to_<sample_attr>, where
    <kb_attr> is a key in KB_SAMPLE_COEFFICIENTS with dots replaced by
    underscores for use as keyword arguments.

    For nested axes (e.g. 'theta_y.coarse'), use the dict form since Python
    does not allow dots in keyword argument names:

        set_kb_correction({"theta_y.coarse_to_x": 0.5})

    Top-level axes can use either form:

        set_kb_correction(x_to_x=0.001)
        set_kb_correction({"x_to_x": 0.001})

    Unmentioned coefficients keep their current values.

    Parameters
    ----------
    coefficients : dict, optional
        Plain dict of <kb_attr>_to_<sample_attr> keys and float values.
        Use this form for dotted axes like 'theta_y.coarse'.
    **kwargs : float values keyed by <kb_attr>_to_<sample_attr> names.
        Convenient form for top-level axes without dots in their names.

    Returns
    -------
    dict — the updated KB_SAMPLE_COEFFICIENTS for inspection.

    Examples
    --------
        set_kb_correction(x_to_x=0.001, theta_y_to_x=0.0)
        set_kb_correction({"theta_y.coarse_to_x": 0.0015797, "theta_y.fine_to_x": 0.0015797})
    """
    if coefficients:
        kwargs.update(coefficients)

    # Build a reverse lookup: "theta_y.coarse_to_x" -> ("theta_y.coarse", "x")
    # Dots in kb_attr are preserved in the key; callers use the dict form for these.
    valid_keys = {
        f"{kb_attr}_to_{sample_attr}": (kb_attr, sample_attr)
        for kb_attr, (sample_attr, _) in KB_SAMPLE_COEFFICIENTS.items()
    }

    unknown = set(kwargs) - set(valid_keys)
    if unknown:
        raise ValueError(
            f"Unknown coefficient name(s): {unknown}. "
            f"Valid names: {sorted(valid_keys)}"
        )

    for key, value in kwargs.items():
        kb_attr, sample_attr = valid_keys[key]
        KB_SAMPLE_COEFFICIENTS[kb_attr] = (sample_attr, float(value))
        logger.info("KB correction updated: %s = %s", key, value)

    return KB_SAMPLE_COEFFICIENTS

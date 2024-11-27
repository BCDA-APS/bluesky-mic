"""Bluesky plans."""

# Simulated plans to test out installation
from .sim_plans import sim_count_plan  # noqa: F401, I001
from .sim_plans import sim_print_plan  # noqa: F401
from .sim_plans import sim_rel_scan_plan  # noqa: F401

## Plans designed for ISN

# from .test import test_plan  # noqa: F401
# from .fl1d import fly  # noqa: F401 only works on eric's system
# from .scan_record_scan import scan_record_isn
from .fly2d_2idsft import fly2d  # noqa: F401
# from .profile_move_scan import profile_move_isn  # noqa: F401


# TODO: listobjects get run when loading plans
# TODO: add small documentations

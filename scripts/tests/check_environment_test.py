#!/usr/bin/env python

"""
configure the Bluesky framework
"""

from isn_bs_instrument.tests.check_dm import check_dm
from isn_bs_instrument.tests.check_subnet import warn_if_not_aps_controls_subnet

warn_if_not_aps_controls_subnet()
check_dm()

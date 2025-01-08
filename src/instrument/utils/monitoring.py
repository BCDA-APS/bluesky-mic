"""
Creating a list of scan monitoring function so that Bluesky Plans can subscribe to it

@author: yluo(grace227)

List of functions::

    # # watch_counter( ... ): # Monitor and log the counter value
    # RE(scan_record2(scanrecord_name = 'scan1', ioc = "2idsft:", m1_name = 'm1',
    #                m1_start = -0.5, m1_finish = 0.5,
    #                m2_name = 'm3', m2_start = -0.2 ,m2_finish = 0.2, 
    #                npts = 50, dwell_time = 0.1))

"""

import logging
from functools import partial
logger = logging.getLogger(__name__)
logger.info(__file__)


def watch_counter(set_point):
    f = partial(_watch_counter, set_point = set_point)
    return f


def _watch_counter(set_point, old_value, value, *args, **kwargs):
    if type(old_value) is not object:
        if all([value > 0, value > old_value]):
            prog = round(100 * value / set_point, 2)
            logger.info(f"Scan progress: {prog}% done, scanned {value}/{set_point}")
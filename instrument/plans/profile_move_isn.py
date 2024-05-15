"""
Creating a bluesky plan that interacts with profile move.

EXAMPLE::

    # Load this code in IPython or Jupyter notebook:
    %run -i user/profile_move_isn.py

    # Run the plan with the RunEngine:
    RE(profile_move_isn(profilemove_name = 'pm1:', ioc = "2idsft:", 
                     m1_name = 'm1', m1_start = -0.5, m1_finish = 0.5,
                     m2_name = 'm2', m2_start = -0.2 ,m2_finish = 0.2, dwell_time = 0.1))
"""

__all__ = """
    profile_move_isn
""".split()

import logging

from ophyd import Device, EpicsSignal
from ophyd.status import Status, DeviceStatus
import bluesky.plan_stubs as bps
from apstools.plans import run_blocking_function
from epics import caput
import numpy as np
import time

# from ophyd import Component as Cpt
# from bluesky import plans as bp


logger = logging.getLogger(__name__)
logger.info(__file__)

class ProfileMove:
    #setup profile move device
    def __init__(self, ioc, profilemove_name):
   
        self.abort = EpicsSignal(f'{ioc}{profilemove_name}Abort')
        self.num_points = EpicsSignal(f'{ioc}{profilemove_name}NumPoints')
        self.timer_mode = EpicsSignal(f'{ioc}{profilemove_name}TimeMode')
        self.accel = EpicsSignal(f'{ioc}{profilemove_name}Acceleration')
        self.num_pulses = EpicsSignal(f'{ioc}{profilemove_name}NumPulses')
        self.m1_arr = EpicsSignal(f'{ioc}{profilemove_name}M1Positions')
        self.m1_proc = EpicsSignal(f'{ioc}{profilemove_name}M1Positions.PROC')
        self.m1_use = EpicsSignal(f'{ioc}{profilemove_name}M1UseAxis')
        self.m2_arr = EpicsSignal(f'{ioc}{profilemove_name}M2Positions')
        self.m2_proc = EpicsSignal(f'{ioc}{profilemove_name}M2Positions.PROC')
        self.m2_use = EpicsSignal(f'{ioc}{profilemove_name}M2UseAxis')
        self.m3_arr = EpicsSignal(f'{ioc}{profilemove_name}M3Positions')
        self.m3_proc = EpicsSignal(f'{ioc}{profilemove_name}M3Positions.PROC')
        self.m3_use = EpicsSignal(f'{ioc}{profilemove_name}M3UseAxis')
        self.m4_arr = EpicsSignal(f'{ioc}{profilemove_name}M4Positions')
        self.m4_proc = EpicsSignal(f'{ioc}{profilemove_name}M4Positions.PROC')
        self.m4_use = EpicsSignal(f'{ioc}{profilemove_name}M4UseAxis')
        self.m5_arr = EpicsSignal(f'{ioc}{profilemove_name}M5Positions')
        self.m5_proc = EpicsSignal(f'{ioc}{profilemove_name}M5Positions.PROC')
        self.m5_use = EpicsSignal(f'{ioc}{profilemove_name}M5UseAxis')
        self.m6_arr = EpicsSignal(f'{ioc}{profilemove_name}M6Positions')
        self.m6_proc = EpicsSignal(f'{ioc}{profilemove_name}M6Positions.PROC')
        self.m6_use = EpicsSignal(f'{ioc}{profilemove_name}M6UseAxis')
        self.times = EpicsSignal(f'{ioc}{profilemove_name}Times')
        self.fixed_time = EpicsSignal(f'{ioc}{profilemove_name}FixedTime')
        self.build = EpicsSignal(f'{ioc}{profilemove_name}Build')
        self.exsc = EpicsSignal(f'{ioc}{profilemove_name}Execute', kind="omitted")
        self.readback = EpicsSignal(f'{ioc}{profilemove_name}Readback')
        self.exsc_state = EpicsSignal(f'{ioc}{profilemove_name}ExecuteState')
        self.move_mode = EpicsSignal(f'{ioc}{profilemove_name}MoveMode')

    #TODO: reset function

    
    def wait_for_connection(self):
        time.sleep(3)
        #TODO: this needs to be re-implemented for profile move, not sure how it's done for SscanRecord

    
    print("exit in setup_scan function")

def setup_profile_move(pm1, xarr, yarr, dwell_time):
    print("in setup_profile_move function")
    pm1.wait_for_connection()
    # yield from run_blocking_function(pm1.abort) # TODO: re-implement reset function for profile move
    yield from bps.sleep(0.2)  # arbitrary wait for EPICS to finish the reset.
    yield from bps.mv(
        pm1.m1_use, 1,
        pm1.m2_use, 1)
    
    # m1_arr and m2_arr assignment
    caput(pm1.m1_arr.pvname, xarr)
    caput(pm1.m2_arr.pvname, yarr)

    yield from bps.mv(
        pm1.m1_arr, xarr, 
        pm1.m2_arr, yarr, 
        pm1.num_points, len(xarr), 
        pm1.timer_mode, 0, 
        pm1.accel, 0, 
        pm1.fixed_time, dwell_time,
    ) 

    yield from bps.trigger(pm1.m1_proc)
    yield from bps.trigger(pm1.m2_proc)
    yield from bps.trigger(pm1.build)

    caput(pm1.build.pvname, 1)

        
    print("exit in setup_scan function")



def profile_move_isn(ioc="2idsft:", pm_name="pm1:", m1_start = -0.5, m1_finish = 0.5, 
                     m2_start = -0.2 ,m2_finish = 0.2, dwell_time = 0.1,
                     xpts = 10, ypts = 10):
    
    """Simple bluesky plan for demonstrating 2D raster scan."""
    param_labels = ['pm_name', 'ioc', 'm1_start', 'm1_finish', 'm2_start', 'm2_finish', 'dwell_time']

    for l in param_labels:
        print(f"plan starts with {l}={eval(l)}")

    """Set up profile move"""
    print("in profile_move function")
    pm1 = ProfileMove(ioc=ioc, profilemove_name=pm_name)
    m1_arr = np.linspace(m1_start, m1_finish, xpts)
    m2_arr = np.linspace(m2_start, m2_finish, ypts)
    xx, yy = np.meshgrid(m1_arr, m2_arr)
    xarr = xx.flatten()
    yarr= yy.flatten()
    yield from setup_profile_move(pm1, xarr, yarr, dwell_time=dwell_time)

    """Start executing scan"""
    st = Status()
    print("Done setting up scan record, about to start scan")

    def watch_execute_scan(old_value, value, **kwargs):
        # Watch for scan1.EXSC to change from 1 to 0 (when the scan ends).
        if old_value == (1 or 2 or 3)  and value == 0:
            # mark as finished (successfully).
            st.set_finished()

            # Remove the subscription.
            pm1.exsc.clear_sub(watch_execute_scan)

    # yield from bps.mv(pm1.exec, 1)
    caput(pm1.exsc.pvname, 1)
    # pm1.exsc.subscribe(watch_execute_scan)
    # yield from run_blocking_function(st.wait)

    print("end of plan\n")



############# Example code to run in ipython terminal####################
# RE = bluesky.RunEngine()
# ioc = "2idsft:"
# profilemove_name = "pm1:"
# pm1 = ProfileMove(ioc=ioc, profilemove_name=profilemove_name)

# RE(profile_move_isn(pm1, m1_start = -0.5, m1_finish = 0.5, m2_start = -0.2 ,
                    # m2_finish = 0.2, dwell_time = 0.1, xpts = 12, ypts=12))
# RE(setup_profile_move(pm1=pm1, profilemove_name=profilemove_name, ioc=ioc, m1_name=m1_name, m2_name=m2_name,
#                 m1_start=m1_start, m1_finish=m1_finish, m2_start=m2_start, 
#                 m2_finish=m2_finish, npts=npts, dwell_time=dwell_time))
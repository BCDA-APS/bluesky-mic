"""
Bluesky suspenders for APS shutter monitoring.

Suspenders pause the RunEngine automatically when a monitored signal goes
into a bad state, and resume it (after an optional sleep) once the condition
clears — without any user intervention.

Suspenders defined here
-----------------------
suspender  : pauses when the Front-End Shutter (FES) closes.
             Waits 20 minutes after it reopens before resuming, to allow
             the beam to stabilise.
suspender2 : pauses when the Secondary Enclosure Shutter (SES) closes.
             Resumes 2 seconds after it reopens.

Installation (add to startup.py after make_devices())
------------------------------------------------------
    from isn.suspenders.suspender import suspender, suspender2
    RE.install_suspender(suspender)
    RE.install_suspender(suspender2)

Removing a single suspender
----------------------------
    RE.remove_suspender(suspender)

Removing all suspenders
-----------------------
    RE.clear_suspenders()

Checking installed suspenders
------------------------------
    RE.suspenders          # dict of installed suspender objects
"""

from ophyd import EpicsSignalRO
from bluesky.suspenders import SuspendBoolHigh

suspender = SuspendBoolHigh(
    EpicsSignalRO("19ID:BLEPS:FES_CLOSED", 
                  name="a_susp"),
    sleep = 1200, 
    )

e_suspender = SuspendBoolHigh(
    EpicsSignalRO("19ID:BLEPS:SES_CLOSED", 
                  name="e_susp"),
    sleep = 2, 
    )
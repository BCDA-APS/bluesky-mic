"""Profile Move Interface."""


__all__ = """
    pm1
    setup_profile_move
""".split()

from bluesky import plan_stubs as bps
from epics import caput  # FIXME: refactor with bps.mv
from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO


class ProfileMove(Device):
    abort = Component(EpicsSignal, 'Abort')
    num_points = Component(EpicsSignal, 'NumPoints')
    timer_mode = Component(EpicsSignal, 'TimeMode')
    accel = Component(EpicsSignal, 'Acceleration')
    num_pulses = Component(EpicsSignal, 'NumPulses')
    m1_arr = Component(EpicsSignal, 'M1Positions')
    m1_proc = Component(EpicsSignal, 'M1Positions.PROC')
    m1_use = Component(EpicsSignal, 'M1UseAxis')
    m2_arr = Component(EpicsSignal, 'M2Positions')
    m2_proc = Component(EpicsSignal, 'M2Positions.PROC')
    m2_use = Component(EpicsSignal, 'M2UseAxis')
    m3_arr = Component(EpicsSignal, 'M3Positions')
    m3_proc = Component(EpicsSignal, 'M3Positions.PROC')
    m3_use = Component(EpicsSignal, 'M3UseAxis')
    m4_arr = Component(EpicsSignal, 'M4Positions')
    m4_proc = Component(EpicsSignal, 'M4Positions.PROC')
    m4_use = Component(EpicsSignal, 'M4UseAxis')
    m5_arr = Component(EpicsSignal, 'M5Positions')
    m5_proc = Component(EpicsSignal, 'M5Positions.PROC')
    m5_use = Component(EpicsSignal, 'M5UseAxis')
    m6_arr = Component(EpicsSignal, 'M6Positions')
    m6_proc = Component(EpicsSignal, 'M6Positions.PROC')
    m6_use = Component(EpicsSignal, 'M6UseAxis')
    times = Component(EpicsSignal, 'Times')
    fixed_time = Component(EpicsSignal, 'FixedTime')
    build = Component(EpicsSignal, 'Build.PROC')
    exsc = Component(EpicsSignal, 'Execute', kind="omitted")
    readback = Component(EpicsSignalRO, 'Readback')
    exsc_state = Component(EpicsSignal, 'ExecuteState')
    move_mode = Component(EpicsSignal, 'MoveMode')

    def setup_profile_move(self, xarr, yarr, dwell_time):
        print("in setup_profile_move function")
        self.wait_for_connection()
        # yield from run_blocking_function(pm1.abort) # TODO: re-implement reset function for profile move
        yield from bps.sleep(0.2)  # arbitrary wait for EPICS to finish the reset.
        caput(self.m1_arr.pvname, list(xarr))  # FIXME: replace with yield from bps.mv()
        caput(self.m2_arr.pvname, list(yarr))
        yield from bps.mv(
            self.m1_use, 1,
            self.m2_use, 1,
            self.num_points, len(xarr),
            self.accel, 0,
            self.timer_mode, 0,
            self.fixed_time, dwell_time,
            # pm1.m1_arr, list(xarr),
            # pm1.m2_arr, list(yarr),
            self.m1_proc,1,
            self.m2_proc,1,
            self.build, 1
            )
        print("exit in setup_profile_move function")

pm1 = ProfileMove("2idsft:", name="pm1")
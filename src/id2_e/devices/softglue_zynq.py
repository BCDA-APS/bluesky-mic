__all__ = """
    sgz
""".split()

import bluesky.plan_stubs as bps
from epics import caput
from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal


class SoftGlueZynq(Device):
    """Device class for SoftGlue Zynq at ID2-E beamline."""

    npts = Component(EpicsSignal, "SG:plsTrn-1_NPULSES")
    period = Component(EpicsSignal, "SG:plsTrn-1_PERIOD")
    width = Component(EpicsSignal, "SG:plsTrn-1_WIDTH")
    clr1_proc = Component(EpicsSignal, "SG:UpDnCntr-1_CLEAR_Signal.PROC")
    clr2_proc = Component(EpicsSignal, "SG:UpDnCntr-2_CLEAR_Signal.PROC")
    clrcntr_proc = Component(EpicsSignal, "SG:UpCntr-1_CLEAR_Signal.PROC")
    clr_C = Component(EpicsSignal, "1acquireDma.C")
    clr_F = Component(EpicsSignal, "1acquireDma.F")
    clr_D = Component(EpicsSignal, "1acquireDma.D")
    VALF = Component(EpicsSignal, "1acquireDma.VALF")
    VALG = Component(EpicsSignal, "1acquireDma.VALG")
    VALC = Component(EpicsSignal, "1acquireDma.VALC")
    enbl_dma = Component(EpicsSignal, "1acquireDmaEnable")
    usrclk_enable = Component(EpicsSignal, "SG:DivByN-3_ENABLE_Signal.PROC")
    rst_buffer = Component(EpicsSignal, "SG:BUFFER-1_IN_Signal.PROC")
    send_pulses = Component(EpicsSignal, "SG:plsTrn-1_Inp_Signal.PROC")

    def setup_softgluezynq(sgz, npts, period):
        print("in setup_softgluezinq function")
        clk_f = int(20e6)  # master clock
        period = int(period * clk_f)  # period in number of clock cycles
        width = int(period / 2)  # duty cycle 50%

        caput(sgz.usrclk_enable.pvname, "0")  # disable user clock
        caput(sgz.enbl_dma.pvname, 0)  # disable user clock

        yield from bps.mv(
            sgz.npts,
            npts,  # set npts
            sgz.period,
            period,  # set period in # of clock cycles
            sgz.width,
            width,  # pulse width in # of clock cycles
            sgz.clr1_proc,
            1,  # clear interferometer 1
            sgz.clr2_proc,
            1,  # clear interfoerometer 2
            sgz.clr_D,
            1,  # clears plots
            sgz.enbl_dma,
            1,  # enables position collection
        )

        caput(sgz.usrclk_enable.pvname, "0")  # enables user clock


# pv = iconfig.get("DEVICES")["SOFT_GLUE"]
# sgz = SoftGlueZynq(pv, name="sgz")

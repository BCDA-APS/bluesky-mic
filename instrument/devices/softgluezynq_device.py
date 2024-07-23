"""SoftGlueZynq (FPGA)."""

from bluesky import plan_stubs as bps
from epics import caput  # FIXME: refactor with bps.mv
from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal


class SoftGlueZynq(Device):
    npts = Component(EpicsSignal, 'SG:plsTrn-1_NPULSES')
    period = Component(EpicsSignal, 'SG:plsTrn-1_PERIOD')
    width = Component(EpicsSignal, 'SG:plsTrn-1_WIDTH')
    clr1_proc = Component(EpicsSignal, 'SG:UpDnCntr-1_CLEAR_Signal.PROC')
    clr2_proc = Component(EpicsSignal, 'SG:UpDnCntr-2_CLEAR_Signal.PROC')
    clrcntr_proc = Component(EpicsSignal, 'SG:UpCntr-1_CLEAR_Signal.PROC')
    clr_C = Component(EpicsSignal, '1acquireDma.C')
    clr_F = Component(EpicsSignal, '1acquireDma.F')
    clr_D = Component(EpicsSignal, '1acquireDma.D')
    VALF = Component(EpicsSignal, '1acquireDma.VALF')
    VALG = Component(EpicsSignal, '1acquireDma.VALG')
    VALC = Component(EpicsSignal, '1acquireDma.VALC')
    enbl_dma = Component(EpicsSignal, '1acquireDmaEnable')
    usrclk_enable = Component(EpicsSignal, 'SG:DivByN-3_ENABLE_Signal.PROC')
    rst_buffer = Component(EpicsSignal, 'SG:BUFFER-1_IN_Signal.PROC')
    send_pulses = Component(EpicsSignal, 'SG:plsTrn-1_Inp_Signal.PROC')

    def setup_softgluezynq(self, npts, frequency):
        print("in setup_softgluezynq function")
        clk_f = 20E6 # master clock
        period = int(clk_f/frequency) #period in number of clock cycles
        width = int(0.000001 * clk_f) #1us in number of clock cycles

        # TODO: Why are enable AND disable both "0"?
        caput(self.usrclk_enable.pvname, "0") #disable user clock
        # TODO: yield from bps.mv(self.usrclk_enable, "0")
        yield from bps.mv(self.enbl_dma, 0)   #disable position collection

        yield from bps.mv(
            self.npts, npts,       #set npts
            self.period, period,   #set period in # of clock cycles
            self.width, width,     #pulse width in # of clock cycles
            self.clr1_proc, 1,     #clear interferometer 1
            self.clr2_proc, 1,     #clear interfoerometer 2
            # sgz.clr_C, 1,         #clears SOMETHING
            # sgz.clr_F, 1,         #clears clears cbuff
            self.clr_D, 1,         #clears plots
            # sgz.rst_buffer, 1,    #resets buff (do i need this?)
            self.enbl_dma, 1,      #enables position collection
            )
        caput(self.usrclk_enable.pvname, "0") #enables user clock
        # TODO: yield from bps.mv(self.usrclk_enable, "0")
        print("exit setup_softgluezynq function")

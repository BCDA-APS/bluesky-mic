'''
SoftGlueZynq implementation for ISN
'''

__all__ = ['softglue']

from ophyd import Device, Component, EpicsSignal, EpicsSignalRO
from collections import OrderedDict
from bluesky.plan_stubs import mv

class UpCounter(Device):
    enable = Component(EpicsSignal, "ENABLE_Signal", kind='config')
    clock = Component(EpicsSignal, "CLK_Signal", kind='config')
    clear = Component(EpicsSignal, "CLEAR_Signal", kind='config')
    counts = Component(EpicsSignalRO, "Counts", kind='config')

class DownCounter(Device):
    enable = Component(EpicsSignal, "ENABLE_Signal", kind='config')
    clock = Component(EpicsSignal, "CLK_Signal", kind='config')
    load = Component(EpicsSignal, "LOAD_Signal", kind='config')
    preset = Component(EpicsSignal, "PRESET", kind='config')
    out_signal = Component(EpicsSignal, "OUT_Signal", kind='config')

class Buffer(Device):
    in_signal = Component(EpicsSignal, "IN_Signal", kind='config')
    out_signal = Component(EpicsSignal, "OUT_Signal", kind='config')

class DivByN(Device):
    enable = Component(EpicsSignal, "ENABLE_Signal", kind='config')
    clock = Component(EpicsSignal, "CLOCK_Signal", kind='config')
    reset = Component(EpicsSignal, "RESET_Signal", kind='config')
    n = Component(EpicsSignal, "N", kind='config')
    out_signal = Component(EpicsSignal, "OUT_Signal", kind='config')

class GateDelay(Device):
    in_signal = Component(EpicsSignal, "IN_Signal", kind='config')
    clock = Component(EpicsSignal, "CLK_Signal", kind='config')
    delay = Component(EpicsSignal, "DLY", kind='config')
    width = Component(EpicsSignal, "WIDTH", kind='config')
    out_signal = Component(EpicsSignal, 'OUT_Signal', kind='config')


class SoftGlueZynq(Device):
    #TODO: Make an ordered dictionary implementation for components
    buffer_1 = Component(Buffer, "BUFFER-1_", kind='config')
    buffer_2 = Component(Buffer, "BUFFER-2_", kind='config')
    buffer_3 = Component(Buffer, "BUFFER-3_", kind='config')
    buffer_4 = Component(Buffer, "BUFFER-4_", kind='config')

    div_by_n_1 = Component(DivByN, "DivByN-1_", kind='config') #1 MHz clock
    div_by_n_2 = Component(DivByN, "DivByN-2_", kind='config') 
    div_by_n_3 = Component(DivByN, "DivByN-3_", kind='config') #Usr clock
    div_by_n_4 = Component(DivByN, "DivByN-4_", kind='config')

    up_counter_1 = Component(UpCounter, "UpCntr-1") #1 MHz clock
    up_counter_2 = Component(UpCounter, "UpCntr-1") #Usr clock
    up_counter_3 = Component(UpCounter, "UpCntr-1")
    up_counter_4 = Component(UpCounter, "UpCntr-1")

    gate_delay_1 = Component(GateDelay, "GateDly-1")

    def start(self):
        yield from mv(self.buffer_4.in_signal, "1")

    def setup_gated_trigger(self, period_time, pulse_width, pulse_delay=0):
        yield from mv(
            self.div_by_n_3.n, 1e7*period_time,
            self.gate_delay_1.delay, 1e7*pulse_delay,
            self.gate_delay_1.width, 1e7*pulse_width
        )







softglue = SoftGlueZynq("acq_isn:SG:", name='softglue')
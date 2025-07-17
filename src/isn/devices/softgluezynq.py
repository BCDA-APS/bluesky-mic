"""SoftGlueZynq implementation for ISN."""

from ophyd import Device, Component, EpicsSignal, EpicsSignalRO, DynamicDeviceComponent
from collections import OrderedDict
from bluesky.plan_stubs import mv, sleep
import numpy as np

def _io_fields(num=16):
    defn = OrderedDict()
    for i in range(1, num+1):
        defn[f"fi{i}"] = (EpicsSignal, f"SG:FI{i}_Signal", {"kind": "config"})
        defn[f"fo{i}"] = (EpicsSignal, f"SG:FO{i}_Signal", {"kind": "config"})
    return defn

def _dma_fields(num=8, first_letter="I"):
    defn = OrderedDict()
    defn["enable"] = (EpicsSignal, "1acquireDmaEnable", {"kind": "config"})
    defn["scan"] = (EpicsSignal, "1acquireDma.SCAN", {"kind": "config"})
    defn["read_button"] = (EpicsSignal, "1acquireDma.PROC", {"kind": "omitted"})
    defn["clear_button"] = (EpicsSignal, "1acquireDma.D", {"kind": "omitted"})
    defn["clear_buffer"] = (EpicsSignal, "1acquireDma.F", {"kind": "omitted"})
    defn["words_in_buffer"] = (
        EpicsSignalRO, "1acquireDma.VALJ", {"kind": "config"}
    )
    defn["events"] = (EpicsSignalRO, "1acquireDma.VALI", {"kind": "config"})
    for i in range(1, num+1):
        defn[f"channel_{i}_name"] = (
            EpicsSignal, f"1s{i}name", {"kind": "config"}
        )
        defn[f"channel_{i}_scale"] = (
            EpicsSignal,
            f"1acquireDma.{chr(ord(first_letter)+i-1)}",
            {"kind": "config"}
        )
    return defn

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
    in_signal = Component(EpicsSignal, "_IN_Signal", kind='config')
    clock = Component(EpicsSignal, "_CLK_Signal", kind='config')
    delay = Component(EpicsSignal, "_DLY", kind='config')
    width = Component(EpicsSignal, "_WIDTH", kind='config')
    out_signal = Component(EpicsSignal, "_OUT_Signal", kind='config')

class PulseTrain(Device):
    clock = Component(EpicsSignal, "_CLK_Signal", kind='config')
    n = Component(EpicsSignal, "_NPULSES", kind='config')
    period = Component(EpicsSignal, "_PERIOD", kind='config')
    width = Component(EpicsSignal, "_WIDTH", kind='config')



class SoftGlueZynq(Device):

    ### Components

    io = DynamicDeviceComponent(_io_fields())

    buffer_1 = Component(Buffer, ":SG:BUFFER-1_", kind='config')
    buffer_2 = Component(Buffer, ":SG:BUFFER-2_", kind='config')
    buffer_3 = Component(Buffer, ":SG:BUFFER-3_", kind='config')
    buffer_4 = Component(Buffer, ":SG:BUFFER-4_", kind='config')

    div_by_n_1 = Component(DivByN, ":SG:DivByN-1_", kind='config') #1 MHz clock
    div_by_n_2 = Component(DivByN, ":SG:DivByN-2_", kind='config') 
    div_by_n_3 = Component(DivByN, ":SG:DivByN-3_", kind='config') #Usr clock
    div_by_n_4 = Component(DivByN, ":SG:DivByN-4_", kind='config')

    up_counter_1 = Component(UpCounter, ":SG:UpCntr-1_") #1 MHz clock
    up_counter_2 = Component(UpCounter, ":SG:UpCntr-1_") #Usr clock
    up_counter_3 = Component(UpCounter, ":SG:UpCntr-1_")
    up_counter_4 = Component(UpCounter, ":SG:UpCntr-1_")

    down_counter_1 = Component(DownCounter, ":SG:DnCntr-1_")

    gate_delay_1 = Component(GateDelay, ":SG:GateDly-1")

    pulse_train = Component(PulseTrain, ":SG:plsTrn-1")

    #Ram memory components for fly scanning
    mem_address = Component(EpicsSignal, ":SG:mem_ADDRA")
    mem_data = Component(EpicsSignal, ":SG:mem_DINA")
    mem_clk = Component(EpicsSignal, ":SG:mem_CLK_Signal")
    mem_write = Component(EpicsSignal, ":SG:mem_WRT_Signal")
    mem_enable = Component(EpicsSignal, ":SG:mem_EN_Signal")

    ram_enable = Component(EpicsSignal, ":SG:driveRAM_en_Signal")
    ram_n = Component(EpicsSignal, ":SG:driveRAM_N")

    dac1_man = Component(EpicsSignal, ":SG:mux32_SEL_Signal")
    dac1_val = Component(EpicsSignal, ":SG:DAC1_VAL")
    dac1_write = Component(EpicsSignal, ":SG:DAC_WRITE_Signal")

    threshold_pos = Component(EpicsSignal, ":SG:threshTrig-1_POSTHR")
    threshold_neg = Component(EpicsSignal, ":SG:threshTrig-1_NEGTHR")

    #DMA components
    dma = DynamicDeviceComponent(_dma_fields())

    ### Functions

    def start(self):
        yield from mv(self.buffer_4.in_signal, "1")
        # self.buffer_4.in_signal.set("1")
        # yield from mv(self.buffer_4.in_signal, "1")

    def stop(self):
        # self.buffer_4.in_signal.set("0")
        yield from mv(self.buffer_4.in_signal, "0")

    def reset(self):
        # self.buffer_1.in_signal.set("1!")
        yield from mv(self.buffer_1.in_signal, "1!")

    def reset_interferometers(self):
        # self.buffer_2.in_signal.set("1!")
        yield from mv(self.buffer_2.in_signal, "1!")

    def setup_gated_trigger(self, period_time, pulse_width, pulse_delay=0):
        yield from mv(
            self.div_by_n_3.n, 1e7*period_time,
            self.gate_delay_1.delay, 1e7*pulse_delay,
            self.gate_delay_1.width, 1e7*pulse_width
        )

    def enable_waveform(self):
        yield from mv(self.mem_enable, "1",
                      self.dac1_man, "0")
        
    def disable_waveform(self):
        yield from mv(self.mem_enable, "0",
                      self.dac1_man, "1")



    def write_RAM(self, array):

        #Tim's function for writing the array in the softglue memory for flyscans
        yield from mv(
            self.mem_write, "1",
            self.ram_enable, "0",
            )
        yield from sleep(0.001)

        for i, j in enumerate(array):
            # yield from mv(
            #     self.mem_address, str(i),
            #     self.mem_data, str(j)
            # )
            self.mem_address.put(i)
            self.mem_data.put(j)

            yield from sleep(0.001)
            yield from mv(self.mem_clk, "1!")
            yield from sleep(0.001)

        yield from mv(
            self.mem_write, "0",
            self.ram_enable, "1",
            # self.ram_n, str(len(array)),
            # self.mem_clk, "ckIM"
            )
        
        self.ram_n.put(str(len(array)))
        self.mem_clk.put("funcGenPulse")
        self.ram_n.put(str(len(array)))
        
    def create_snake_bits(self, A=32767, F=0.9, npts=1000, offset=0):

        # Take one half cycle of a sine wave, from -pi/2 to pi/2 and cut it at
        # the zero crossing. If the sine has amplitude 1, then the slope at the
        # zero crossing is 1. Move both parts of the sine away from the origin
        # along the line x = y. If we want the line to be the fraction, F, of
        # the total y extent, A, and the Y extent of the line is L, then
        # L = F*(L+1), which yields L = F/(1-F).
        L = F/(1.-F)

    
        # We want A to be a user-specified amplitude of the entire function, so
        # a scale factor, Sy, is given by Sy*(L+1) = A.
        Sy = A/(L+1.)
    
        # Then, the function is the line S*L, joined to 1/4 of a sine function
        # with amplitude S,  from 0 to pi/2 . Along the x axis, the line extends
        # over distance L, and the quarter-sine function from 0 to pi/2 extends
        # over pi/2. The total length, in equally spaced points along x, is
        # Sx * (L + pi/2) = npts/4
        Sx = (npts/4.) / (L + np.pi/2)
        # Each quarter-sine function occupies Sx*pi/2 places in the array we're
        # assembling.
        arr1 = np.linspace(-np.pi/2, 0, int(Sx*np.pi/2))
        sinArr1 = Sy*np.sin(arr1)
    
        # The full line function:
        arr2 = np.linspace(-L, L, int(Sx*2*L))
        # The second quarter-sine function:
        arr3 = np.linspace(0, np.pi/2, int(Sx*np.pi/2))
        sinArr3 = Sy*np.sin(arr3)
    
        # The total points in this half of the function:
        Nt = 2*int(Sx*np.pi/2) + int(Sx*2*L) - 2
        # Now we assemble, skipping the first and last points of the line,
        # because their values are already in the quarter-sine functions:
        half = np.concatenate([sinArr1-Sy*L, Sy*arr2[1:-1], sinArr3+Sy*L])
        all = np.concatenate([half, np.flip(half,0)])
    
        # Return the array that needs to be written to the RAM
        return all+offset
    
    def y_to_bits(self, y):
        # Returns the necessay bit value to match the desired y position for
        # the piezo

        if y>90 or y<0:
            raise RuntimeError("Piezo scan requested exceeds 0 um - 90 um range -- Aborting.")
        
        m = (2**15 - 1)/90
        b = -(2**15-1)/2

        return int(m*y+b)

    def snake_y(self, y_min=0, y_max=90, F=0.9, npts=1000):
        #Takes a minimum and maximum y values and writes snake array to RAM

        #TODO: maybe later we can make it scan in opposite direction if max < min.
        y_max_bits = self.y_to_bits(y_max)
        y_min_bits = self.y_to_bits(y_min)
        # amplitude = self.y_to_bits(np.abs(y_max - y_min))
        amplitude = (y_max_bits - y_min_bits)/2
        offset = self.y_to_bits((y_max + y_min)/2)

        snake_array = self.create_snake_bits(A=amplitude, F=F, npts=npts, offset=offset)
        # return snake_array
        yield from self.write_RAM(snake_array)

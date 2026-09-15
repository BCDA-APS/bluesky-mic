from collections import OrderedDict

from ophyd import Device
from ophyd import Signal
from ophyd import Component
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import DynamicDeviceComponent

from ophyd.areadetector.trigger_mixins import TriggerBase
from ophyd.status import StatusBase

import numpy as np


def _cap_fields():
    defn = OrderedDict()
    for i in range(1, 8):
        defn[f'cap{i}'] = (EpicsSignalRO, f':SG:ADC{i}', {'kind': 'normal'})
    return defn

def _interferometer_tracker(if_tracker, num=6):
    defn = OrderedDict()
    for i in range(1, 1 + num):
        defn[f"if{i}"] = (
            EpicsSignal,
            f":SG:IF_tracker-{if_tracker}_IN{i}",
            {"kind": "normal"},
        )
    return defn

def bits_to_mm(bits):
    volts = bits * 10 / 2**17
    mms = volts / 80
    return round(mms, 7)

def interf_to_mm(interf):
    mms = interf * 1e-7
    return round(mms, 7)

class Trigger(TriggerBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs['acq_start'] = 0

    def trigger(self) -> StatusBase:
        return self.acq_start.set('1!')


class IfCapTracker(Device):

    _default_read_attrs = ['caps', 
                           'if_tracker_1', 
                           'if_tracker_2', 
                           'if_tracker_3',
                           'x',
                           'y',
                           'z']
    
    caps = DynamicDeviceComponent(_cap_fields())
    acq_start = Component(EpicsSignal, ':SG:ADC_START_CVT_Signal')

    buffer1 = Component(EpicsSignal, ':SG:BUFFER-1_N_Signal', kind='config')

    if_tracker_1 = DynamicDeviceComponent(_interferometer_tracker(1))
    if_tracker_2 = DynamicDeviceComponent(_interferometer_tracker(2))
    if_tracker_3 = DynamicDeviceComponent(_interferometer_tracker(3, num=3))

    x = Component(Signal, name='x', kind='hinted', value=0)
    y = Component(Signal, name='y', kind='hinted', value=0)
    z = Component(Signal, name='z', kind='hinted', value=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs['acq_start'] = '0'

    def trigger(self):
        return self.acq_start.set('1!')

    def calc_position(self, vals: dict):
        x1 = vals['if_cap_tracker_if_tracker_3_if3']['value'] # 'I15 (X)'
        x2 = vals['if_cap_tracker_if_tracker_2_if4']['value'] # 'I10 (X-us)'
        x3 = vals['if_cap_tracker_if_tracker_2_if5']['value'] # 'I11 (X-ds)'
        y1 = vals['if_cap_tracker_if_tracker_2_if1']['value'] # 'I7 (Y ds)'
        y2 = vals['if_cap_tracker_if_tracker_2_if2']['value'] # 'I8 (Y us-ob)'
        y3 = vals['if_cap_tracker_if_tracker_2_if3']['value'] # 'I9 (Y us-ib)'
        z = vals['if_cap_tracker_if_tracker_2_if6']['value'] # 'I12 (Z)'

        x = round((x1 + x2 + x3) / 3, 7)
        y = round((y1 + y2 + y3) / 3, 7)

        vals[self.x.name] = {'value': x, 'timestamp': vals['if_cap_tracker_if_tracker_3_if3']['timestamp']}
        vals[self.y.name] = {'value': y, 'timestamp': vals['if_cap_tracker_if_tracker_2_if1']['timestamp']}
        vals[self.z.name] = {'value': z, 'timestamp': vals['if_cap_tracker_if_tracker_2_if6']['timestamp']}

        return vals


    def read(self):
        vals =  super().read()
        for key in vals:
            if key.startswith('if_cap_tracker_caps'):
                vals[key]['value'] = bits_to_mm(vals[key]['value'])
            elif key.startswith('if_cap_tracker_if_tracker'):
                vals[key]['value'] = interf_to_mm(vals[key]['value'])

        vals = self.calc_position(vals)
        for sig in (self.x, self.y, self.z):
            sig.put(vals[sig.name]['value'])
        return vals

    def describe(self):
        desc = super().describe()
        new_desc = OrderedDict()
        xyz_keys = {self.x.name, self.y.name, self.z.name}
        for key, entry in desc.items():
            new_entry = dict(entry)
            if key.startswith('if_cap_tracker_caps') or \
                    key.startswith('if_cap_tracker_if_tracker') or \
                    key in xyz_keys:
                new_entry['dtype'] = 'number'
                # Optionally update units:
                new_entry['units'] = 'mm'
            new_desc[key] = new_entry
        return new_desc

    def reset(self):
        self.buffer1.set("1!").wait()
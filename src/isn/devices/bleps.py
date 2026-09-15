from ophyd import Device
from ophyd import Component
from ophyd import FormattedComponent
from ophyd import EpicsSignalRO

class QpcIonPump(Device):

    _default_read_attrs = ['pressure',
                           'current',
                ]

    pressure = Component(EpicsSignalRO, 'Pressure', name='pressure', kind='normal')
    current = Component(EpicsSignalRO, 'Current', name='current', kind='normal')
    voltage = Component(EpicsSignalRO, 'Voltage', name='voltage', kind='normal')

class Bleps(Device):
    """Class for the BLEPS Temperatures monitoring"""

    _default_read_attrs = ['temp1',
                           'temp2',
                           'temp3',
                           'temp4',
                           'temp5',
                           'temp6',
                           'temp7',
                           'temp8',
                           'temp9',
                           'temp10',
                           'temp11',
                           'temp12',
                           'temp13',
                           'temp14',
                           'temp15',
                           'temp16',
                           'temp17',
                           'temp18',
                           'temp19',
                           'temp20',
                           'temp21',
                           'temp22',
                           'pump1',
                           'pump2',
                           'pump3',
                           'pump4',
                           'pump5',
                           'pump12',
                           'pump13',
                           ]

    temp1 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+"TEMP1_CURRENT", name='M12-LatX-Mt', kind='normal')
    temp2 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP2_CURRENT", name='M12-Bend1-Mt', kind='normal')
    temp3 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP3_CURRENT", name='M12-Bend2-Mt', kind='normal')
    temp4 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP4_CURRENT", name='M1-Mask', kind='normal')
    temp5 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP5_CURRENT", name='M2-Mask', kind='normal')
    temp6 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP6_CURRENT", name='HDCM-Bragg-Mt', kind='normal')
    temp7 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP7_CURRENT", name='HDCM-Gap-Mt', kind='normal')
    temp8 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP8_CURRENT", name='HDCM-Pitch-Mt', kind='normal')
    temp9 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP9_CURRENT", name='HDCM-Roll-Mt', kind='normal')
    temp10 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP10_CURRENT", name='HDCM-1st-Xtal-Bott', kind='normal')
    temp11 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP11_CURRENT", name='HDCM-2nd-Xtal-Bott', kind='normal')
    temp12 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP12_CURRENT", name='HDCM-Xtal-Mask', kind='normal')
    temp13 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP13_CURRENT", name='M3-Pitch-Mt', kind='normal')
    temp14 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP14_CURRENT", name='M3-Bend1-Mt', kind='normal')
    temp15 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP15_CURRENT", name='M3-Bend2-Mt', kind='normal')
    temp16 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP16_CURRENT", name='M3-Mask', kind='normal')
    temp17 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP17_CURRENT", name='M1-Inner-Blade', kind='normal')
    temp18 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP18_CURRENT", name='M1-Outer-Blade', kind='normal')
    temp19 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP19_CURRENT", name='M2-Inner-Blade', kind='normal')
    temp20 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP20_CURRENT", name='M2-Outer-Blade', kind='normal')
    temp21 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP21_CURRENT", name='M3-Upper-Blade', kind='normal')
    temp22 = FormattedComponent(EpicsSignalRO, "{temps_prefix}"+ "TEMP22_CURRENT", name='M3-Lower-Blade', kind='normal')

    pump1 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc01_1:', name='WBS', kind='normal')
    pump2 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc01_2:', name='MR1-2', kind='normal')
    pump3 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc01_3:', name='PBS', kind='normal')
    pump4 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc01_4:', name='Mono', kind='normal')
    pump5 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc02_1:', name='MR3', kind='normal')
    pump6 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc02_2:', name='SafetyShutter', kind='normal')
    pump7 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc02_3:', name='Flag2', kind='normal')
    pump8 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc02_4:', name='BPM1-US', kind='normal')
    pump9 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc03_1:', name='BPM1-DS', kind='normal')
    pump10 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc04_1:', name='BPM2-US', kind='normal')
    pump11 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc04_2:', name='BPM2-DS', kind='normal')
    pump12 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc04_3:', name='Transport1', kind='normal')
    pump13 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc04_4:', name='Transport2', kind='normal')
    pump14 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc05_1:', name='IP14', kind='normal')
    pump15 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc05_2:', name='IP15', kind='normal')
    pump16 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc05_3:', name='IP16', kind='normal')
    pump17 = FormattedComponent(QpcIonPump, "{pump_prefix}" + 'qpc05_4:', name='IP17', kind='normal')


    def __init__(self, pump_prefix, temps_prefix, *args, **kwargs):
        self.pump_prefix = pump_prefix
        self.temps_prefix = temps_prefix
        super().__init__(*args, **kwargs)
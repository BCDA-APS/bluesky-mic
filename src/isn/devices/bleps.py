from ophyd import Device
from ophyd import Component
from ophyd import EpicsSignalRO

class Bleps(Device):
    """Class for the BLEPS monitoring"""

    _defaul_read_attrs = ['temp1',
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
                           'temp22']

    temp1 = Component(EpicsSignalRO, 'TEMP1_CURRENT', name='M12-LatX-Mt', kind='normal')
    temp2 = Component(EpicsSignalRO, 'TEMP2_CURRENT', name='M12-Bend1-Mt', kind='normal')
    temp3 = Component(EpicsSignalRO, 'TEMP3_CURRENT', name='M12-Bend2-Mt', kind='normal')
    temp4 = Component(EpicsSignalRO, 'TEMP4_CURRENT', name='M1-Mask', kind='normal')
    temp5 = Component(EpicsSignalRO, 'TEMP5_CURRENT', name='M2-Mask', kind='normal')
    temp6 = Component(EpicsSignalRO, 'TEMP6_CURRENT', name='HDCM-Bragg-Mt', kind='normal')
    temp7 = Component(EpicsSignalRO, 'TEMP7_CURRENT', name='HDCM-Gap-Mt', kind='normal')
    temp8 = Component(EpicsSignalRO, 'TEMP8_CURRENT', name='HDCM-Pitch-Mt', kind='normal')
    temp9 = Component(EpicsSignalRO, 'TEMP9_CURRENT', name='HDCM-Roll-Mt', kind='normal')
    temp10 = Component(EpicsSignalRO, 'TEMP10_CURRENT', name='HDCM-1st-Xtal-Bott', kind='normal')
    temp11 = Component(EpicsSignalRO, 'TEMP11_CURRENT', name='HDCM-2nd-Xtal-Bott', kind='normal')
    temp12 = Component(EpicsSignalRO, 'TEMP12_CURRENT', name='HDCM-Xtal-Mask', kind='normal')
    temp13 = Component(EpicsSignalRO, 'TEMP13_CURRENT', name='M3-Pitch-Mt', kind='normal')
    temp14 = Component(EpicsSignalRO, 'TEMP14_CURRENT', name='M3-Bend1-Mt', kind='normal')
    temp15 = Component(EpicsSignalRO, 'TEMP15_CURRENT', name='M3-Bend2-Mt', kind='normal')
    temp16 = Component(EpicsSignalRO, 'TEMP16_CURRENT', name='M3-Mask', kind='normal')
    temp17 = Component(EpicsSignalRO, 'TEMP17_CURRENT', name='M1-Inner-Blade', kind='normal')
    temp18 = Component(EpicsSignalRO, 'TEMP18_CURRENT', name='M1-Outer-Blade', kind='normal')
    temp19 = Component(EpicsSignalRO, 'TEMP19_CURRENT', name='M2-Inner-Blade', kind='normal')
    temp20 = Component(EpicsSignalRO, 'TEMP20_CURRENT', name='M2-Outer-Blade', kind='normal')
    temp21 = Component(EpicsSignalRO, 'TEMP21_CURRENT', name='M3-Upper-Blade', kind='normal')
    temp22 = Component(EpicsSignalRO, 'TEMP22_CURRENT', name='M3-Lower-Blade', kind='normal')
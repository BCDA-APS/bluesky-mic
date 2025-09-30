from ophyd import (
    Device, 
    Component, 
    EpicsMotor, 
    EpicsSignal,
    EpicsSignalRO,
    FormattedComponent,
    )

class CapSensor(Device):

    pos = Component(EpicsSignalRO, "pos", name='pos')
    voltage = Component(EpicsSignalRO, "voltage", name='voltage')
    um_per_v = Component(EpicsSignalRO, "umPerV", name='um_per_v')
    offset = Component(EpicsSignal, "offset", name='offset')

class CapSensorMotor(EpicsMotor):

    cap_sensor = FormattedComponent(CapSensor, '{_cap_sensor_pv}', name='cap_sensor')
    coarse = None
    fine = None

    def __init__(self,
                 positioner_pv, 
                 cap_sensor_pv, 
                 coarse_pv=None, 
                 fine_pv=None,  
                 *args, **kwargs):
        
        self._cap_sensor_pv = cap_sensor_pv
        super().__init__(positioner_pv, *args, **kwargs)

        #TODO: Find a better way to implement this in case a motor doesn't have fine or coarse
        if coarse_pv:
            self._coarse_pv = coarse_pv
            self.coarse = EpicsMotor(self._coarse_pv, name='coarse')
        if fine_pv:
            self._fine_pv = fine_pv
            self.fine = EpicsMotor(self._fine_pv, name='fine')

class KB(Device):

    x = Component(CapSensorMotor,
                  positioner_pv="19idKB:m18",
                  cap_sensor_pv="19idKB:cap4:",
                  coarse_pv='19idKB:m12',
                  fine_pv='19idKB:m6',
                  name='x')
    
    y_ds = Component(CapSensorMotor,
                  positioner_pv="19idKB:m16",
                  cap_sensor_pv="19idKB:cap2:",
                  coarse_pv='19idKB:m11',
                  fine_pv='19idKB:m2',
                  name='x')
    
    y_us = Component(CapSensorMotor,
                  positioner_pv="19idKB:m15",
                  cap_sensor_pv="19idKB:cap1:",
                  coarse_pv='19idKB:m7',
                  fine_pv='19idKB:m1',
                  name='x')
    
    z = Component(CapSensorMotor,
                  positioner_pv="19idKB:m17",
                  cap_sensor_pv="19idKB:cap3:",
                  coarse_pv='19idKB:m8',
                  fine_pv='19idKB:m5',
                  name='z')
    
    theta_y = Component(CapSensorMotor,
                  positioner_pv="19idKB:SM1",
                  cap_sensor_pv="19idKB:cap5:",
                  coarse_pv='19idKB:m9',
                  fine_pv='19idKB:m4',
                  name='theta_y')
    
    theta_z = Component(CapSensorMotor,
                  positioner_pv="19idKB:SM2",
                  cap_sensor_pv="19idKB:cap6:",
                  coarse_pv='19idKB:m10',
                  name='theta_z')
    

    

    

    # def __init__(self, prefix, *args, **kwargs):
    #     super().__init__(prefix, *args, **kwargs)





        



        

# class KB(Device):
#     # th_x = Component(EpicsMotor, ':m9', kind='config', labels=('motor',)) #Need to think right way of implementing it
#     th_y = Component(EpicsMotor, ':SM1', kind='config', labels=('motor','baseline')) 
#     th_y_cap = Component(EpicsSignal, ':cap5:voltage', kind='config', labels=('baseline'))
#     th_z = Component(EpicsMotor, ':SM2', kind='config', labels=('motor','baseline'))
#     th_z_cap = Component(EpicsSignal, ':cap6:voltage', kind='config', labels=('baseline'))
#     x = Component(EpicsMotor, ':m18', kind='config', labels=('motor',))
#     x_cap = Component(EpicsSignal, ':cap4:voltage', kind='config', labels=('baseline'))
#     # y = Component(EpicsMotor, ':m9', kind='config', labels=('motor',)) #Need to think how to do it properly
#     z = Component(EpicsMotor, ':m17', kind='config', labels=('motor',))
#     z_cap = Component(EpicsSignal, ':cap3:voltage', kind='config', labels=('baseline'))
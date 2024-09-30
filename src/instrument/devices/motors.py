"""
example motors
"""

__all__ = """
    x_motor
    y_motor
    z_motor
    r_motor
    xz_motor
    energy
    temperature
""".split()

import logging

logger = logging.getLogger(__name__)
logger.info(__file__)

from .. import iconfig
from ophyd import EpicsMotor, Component, EpicsSignal
from ophyd import MotorBundle, EpicsMotor
from ophyd import Component as Cpt

class myBundle(MotorBundle):
    def __init__(self, value):
        self.value = value

positioners = iconfig.get("POSITIONERS")
#get all configured motors from config file, if group of motors: create motor bundle. else: create regular epics motor
#dynamically set variable names to these motors based on config file. TODO: see if you cen dynamically populate the __all__ string
for positioner in positioners:
    #if motor group
    if isinstance(positioners[positioner], dict): 
        #convert AXIS_MOTOR to lowercase axis_motor
        posnr = positioners.lower()
        #set the lower-case name as a local variable
        locals()[posnr] = myBundle()  
        #assign individual motors to mtorbundle             
        for motor in positioner.keys():           
            setattr(posnr, motor, positioners[positioner][motor])
    else:
        #if single motor, assign it to an EpicsMotor, dynamically specify PV and name
        locals()[posnr] =  EpicsMotor(f"{positioners[positioner]}", name=f"{posnr}", labels=("motor",))



# class StageXY(MotorBundle):
#     x = Cpt(EpicsMotor, ':X')
#     y = Cpt(EpicsMotor, ':Y')


m1.wait_for_connection()

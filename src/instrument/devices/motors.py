"""
example motors
"""

# __all__ = """
#     x_motor
#     y_motor
#     z_motor
#     r_motor
#     xz_motor
#     energy
#     temperature
# """.split()


import logging
logger = logging.getLogger(__name__)
logger.info(__file__)

from .. import iconfig
from ophyd import EpicsMotor, Component, EpicsSignal
from ophyd import MotorBundle, EpicsMotor
from ophyd import Component as Cpt


positioners = iconfig.get("POSITIONERS")
__all__ = [positioner.lower() for positioner in positioners.keys()]


class myBundle(MotorBundle):
    def __init__(self, value):
        self.name = "name"

#get all configured motors from config file, if group of motors: create motor bundle. else: create regular epics motor
#dynamically set variable names to these motors based on config file. TODO: see if you cen dynamically populate the __all__ string
for positioner in positioners:
    #convert AXIS_MOTOR to lowercase axis_motor
    posnr = positioners.lower()
    #if motor group
    if isinstance(positioners[positioner], dict): 
        #set the lower-case name as a local variable
        locals()[posnr] = myBundle()  
        #assign individual motors to mtorbundle             
        for motor in positioner.keys():           
            setattr(posnr, motor, positioners[positioner][motor])
    else:
        #if single motor, assign it to an EpicsMotor, dynamically specify PV and name
        locals()[posnr] =  EpicsMotor(f"{positioners[positioner]}", name=f"{posnr}", labels=("motor",))



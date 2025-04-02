from ophyd import Component as Cpt
from ophyd import EpicsMotor
from ophyd import MotorBundle


# Define your custom MotorBundle class
class MyMotorBundle(MotorBundle):
    """A bundle of motors with prefix 'Eric:'"""

    # Define motors as Components
    m1 = Cpt(EpicsMotor, ":m1")
    m2 = Cpt(EpicsMotor, ":m3")

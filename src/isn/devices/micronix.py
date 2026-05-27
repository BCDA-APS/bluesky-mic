'''
Temporary device implementation for sample micronix stages.
Later, we will need to modify the sample to incorporate this.
'''

import numpy as np
from ophyd import Component
from ophyd import EpicsMotor
# from ophyd import Device
from ophyd import PseudoPositioner
from ophyd import PseudoSingle
from ophyd.pseudopos import pseudo_position_argument
from ophyd.pseudopos import real_position_argument


class Micronix(PseudoPositioner):
    theta = Component(EpicsMotor, "m4")
    mic_x = Component(EpicsMotor, "m3")
    mic_z = Component(EpicsMotor, "m2")

    x = Component(PseudoSingle, limits=(-10, 10))
    z = Component(PseudoSingle, limits=(-10, 10))

    _real = ["theta", "mic_x", "mic_z"]
    _pseudo = ["x", "z"]

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        theta = self.theta.get()[0]
        mic_x = pseudo_pos.x * np.cos(theta * np.pi / 180) - pseudo_pos.z * np.sin(theta * np.pi / 180)
        mic_z = pseudo_pos.x * np.sin(theta * np.pi / 180) + pseudo_pos.z * np.cos(theta * np.pi / 180)
        return self.RealPosition(theta=theta, mic_x=mic_x, mic_z=mic_z)
    
    @real_position_argument
    def inverse(self, real_pos):
        theta = self.theta.get()[0]
        x = real_pos.mic_x * np.cos(theta * np.pi / 180) + real_pos.mic_z * np.sin(theta * np.pi / 180)
        z = -real_pos.mic_x * np.sin(theta * np.pi / 180) + real_pos.mic_z * np.cos(theta * np.pi / 180)
        return self.PseudoPosition(x=x, z=z)

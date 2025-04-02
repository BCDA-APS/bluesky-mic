__all__ = ['mono']


import numpy as np
from ophyd import Component, PseudoPositioner, PseudoSingle, EpicsMotor
from ophyd.pseudopos import pseudo_position_argument, real_position_argument


class Mono(PseudoPositioner):

    bragg = Component(EpicsMotor, 'm1', labels=('motor',))
    gap = Component(EpicsMotor, 'm2', labels=('motor',))
    pitch = Component(EpicsMotor, 'm5', labels=('motor',))
    roll = Component(EpicsMotor, 'm6', labels=('motor',))
    lateral = Component(EpicsMotor, 'm8', labels=('motor',))

    #Specifying the real motors that need to be used for energy change

    _real = ['bragg']
    energy = Component(PseudoSingle, limits=(4.8, 30))

    _crystal_d = 3.135e-10 #in meters
    _hc = 1.2396612e-9 #in keV m

    def energy_to_theta(self, energy):
        '''Energy in keV, returns theta in degrees'''
        lamb = self._hc/energy #energy in keV, returns wavelength in meters
        theta = np.arcsin(lamb/(2*self._crystal_d))*180.0/np.pi
        return theta

    def theta_to_energy(self, theta):
        '''Theta in degrees, returns energy in keV.'''
        lamb = 2*self._crystal_d*np.sin(theta*np.pi/180.0)
        energy = self._hc/lamb
        return energy
    

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        
        return self.RealPosition(
            bragg = self.energy_to_theta(pseudo_pos.energy)
        )
    
    @real_position_argument
    def inverse(self, real_pos):

        return self.PseudoPosition(
            energy = self.theta_to_energy(real_pos.bragg)
        )
    
    def set_energy(self, energy):
        theta = self.energy_to_theta(energy)
        self.bragg.set_current_position(theta)


mono = Mono('19idDCM:', name='mono')






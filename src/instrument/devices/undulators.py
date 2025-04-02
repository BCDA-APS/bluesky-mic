__all__ = ['undulators']


from ophyd import Device, Component
from apstools.devices.aps_undulator import Revolver_Undulator

class ISN_Undulator(Revolver_Undulator):
    #TODO: Implement tracking signal for global energy change
    '''Most of the required functionality comes from the parent class. This function just simplifies changing between devices.'''

    def select_25mm(self):
        #TODO: Implement a wait for finish and return success message when done.
        if self.revolver_select.get() == 1:
            return self.message1.get()
        
        self.revolver_select.set(1)

    def select_21mm(self):
        if self.revolver_select.get() == 0:
            return self.message1.get()
        
        self.revolver_select.set(0)


class UndulatorPair(Device):
    us = Component(ISN_Undulator, "USID:")
    ds = Component(ISN_Undulator, "DSID:")

undulators = UndulatorPair("S19ID:", name='undulators')
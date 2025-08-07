from ophyd import Device
from ophyd import Component
from ophyd import EpicsSignalRO
from ophyd import Signal
from ophyd import EpicsSignal
from ophyd import PVPositioner

from ophyd.status import Status
from ophyd.status import wait as status_wait

from ophyd.utils import InvalidState

from threading import Thread

from apstools.devices import TrackingSignal
from apstools.devices.aps_undulator import Revolver_Undulator



class UndulatorEnergy(PVPositioner):
    """
    Undulator energy positioner from POLAR.

    Always move the undulator to final position from the high to low energy
    direction, by applying a backlash (hysteresis) correction as needed.
    """

    # Position
    readback = Component(EpicsSignalRO, 'Energy', kind='hinted',
                         auto_monitor=True)
    setpoint = Component(EpicsSignal, 'EnergySet', put_complete=True,
                         auto_monitor=True, kind='normal')

    # Configuration
    deadband = Component(Signal, value=0.002, kind='config')
    backlash = Component(Signal, value=0.25, kind='config')
    offset = Component(Signal, value=0, kind='config')

    # Buttons
    actuate = Component(EpicsSignal, "Start.VAL", kind='omitted',
                        put_complete=True)
    actuate_value = 3

    stop_signal = Component(EpicsSignal, "Stop.VAL", kind='omitted')
    stop_value = 1

    done = Component(EpicsSignal, "Busy.VAL", kind="omitted")
    done_value = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tolerance = 0.002
        self.readback.subscribe(self.done.get)
        self.setpoint.subscribe(self.done.get)
        self._status_obj = Status(self)

        # Make the default alias for the readback the name of the
        # positioner itself as in EpicsMotor.
        self.readback.name = self.name

    @deadband.sub_value
    def _change_tolerance(self, value=None, **kwargs):
        if value:
            self.tolerance = value

    def move(self, position, wait=True, **kwargs):
        """
        Moves the undulator energy.

        Currently, the backlash has to be handled within Bluesky. The actual
        motion is done by `self._move` using threading. kwargs are passed to
        PVPositioner.move().

        Parameters
        ----------
        position : float
            Position to move to
        wait : boolean, optional
            Flag to block the execution until motion is completed.

        Returns
        -------
        status : Status
        """

        self._status_obj = Status(self)

        # If position is in the the deadband -> do nothing.
        if abs(position - self.readback.get()) <= self.tolerance:
            self._status_obj.set_finished()

        # Otherwise -> let's move!
        else:
            thread = Thread(target=self._move, args=(position,),
                            kwargs=kwargs)
            thread.start()

        if wait:
            status_wait(self._status_obj)

        return self._status_obj

    def _move(self, position, **kwargs):
        """
        Moves undulator.

        This is meant to run using threading, so the move will block by
        construction.
        """

        # Applies backlash if needed.
        if position > self.readback.get():
            self._move_and_wait(position + self.backlash.get(), **kwargs)

        # Check if stop was requested during first part of the motion.
        if not self._status_obj.done:
            self._move_and_wait(position, **kwargs)
            self._finish_status()

    def _move_and_wait(self, position, **kwargs):
        status = super().move(position, wait=False, **kwargs)
        status_wait(status)

    def _finish_status(self):
        try:
            self._status_obj.set_finished()
        except InvalidState:
            pass

    def stop(self, *, success=False):
        super().stop(success=success)
        self._finish_status()




class ISN_Undulator(Revolver_Undulator):
    #TODO: Implement tracking signal for global energy change
    '''Most of the required functionality comes from the parent class. This 
    function just simplifies changing between devices.'''


    ##TODO: look into more detail on how to adapt polar's solution to the energy 
    # deadband issue

    # energy = Component(UndulatorEnergy, "")
    # tracking = Component(TrackingSignal, value=False, kind='config')

    # start_button = None
    # stop_button = None
    # device_status = None

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
    us = Component(ISN_Undulator, ":USID:")
    ds = Component(ISN_Undulator, ":DSID:")
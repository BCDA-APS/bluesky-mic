from ophyd import PVPositioner, PVPositionerPC, EpicsSignal, EpicsSignalRO
from ophyd import FormattedComponent as FCpt

# Define a new kind of device.

class RobotArmPositioner(PVPositioner):
    """A single axis of the ISN Robot Arm."""

    setpoint = FCpt(EpicsSignal, '{prefix}{pv_setpoint}')
    readback = FCpt(EpicsSignalRO, '{prefix}{pv_readback}')
    actuate= FCpt(EpicsSignal, '{prefix}{pv_execute}')
    done = FCpt(EpicsSignalRO, '{prefix}{pv_done}')
    command = FCpt(EpicsSignal, '{prefix}{pv_command}')

    def stop(self, *, success=False):
        self.command.put("Cancel") #Should we do Pause instead? 
        self.actuate.put(self.actuate_value, wait=False)
        super().stop(success=success)

    def _setup_move(self, position):
        self.command.put("Move")
        super()._setup_move(position)

    def __init__(self, prefix, setpoint, readback, done, execute, command, *args, **kwargs):
        self.pv_setpoint = setpoint
        self.pv_readback = readback
        self.pv_done = done
        self.pv_execute = execute
        self.pv_command = command
        super().__init__(prefix, *args, **kwargs)
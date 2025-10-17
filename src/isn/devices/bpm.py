from ophyd import QuadEM
from ophyd import EpicsSignalRO
from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor
from ophyd import FormattedComponent

from ophyd.areadetector import DetectorBase

from ophyd.device import Staged
from ophyd.status import Status


class BasicQuadEM(Device):

    """Temporary QuadEM implementation for the BPMs. The Sydor epics implementation 
    is still patchy, so it does not work properly with the QuadEM class."""

    fast_current1 = Component(EpicsSignalRO, "Current1Ave")
    fast_current2 = Component(EpicsSignalRO, "Current2Ave")
    fast_current3 = Component(EpicsSignalRO, "Current3Ave")
    fast_current4 = Component(EpicsSignalRO, "Current4Ave")

    fast_position_x = Component(EpicsSignalRO, "PositionXAve")
    fast_position_y = Component(EpicsSignalRO, "PositionYAve")
    

class MyBPM(Device):

    _default_configuration_attrs = ()
    _default_read_attrs = (
        'fast_current1',
        'fast_current2',
        'fast_current3',
        'fast_current4',
    )

    vert = FormattedComponent(EpicsMotor, "{vertical_motor_prefix}")
    hor = FormattedComponent(EpicsMotor, "{horizontal_motor_prefix}")

    fast_current1 = FormattedComponent(EpicsSignalRO, "{quadem_prefix}Current1Ave")
    fast_current2 = FormattedComponent(EpicsSignalRO, "{quadem_prefix}Current2Ave")
    fast_current3 = FormattedComponent(EpicsSignalRO, "{quadem_prefix}Current3Ave")
    fast_current4 = FormattedComponent(EpicsSignalRO, "{quadem_prefix}Current4Ave")

    fast_position_x = FormattedComponent(EpicsSignalRO, "{quadem_prefix}PositionXAve")
    fast_position_y = FormattedComponent(EpicsSignalRO, "{quadem_prefix}PositionYAve")

    def __init__(self, quadem_prefix, vertical_motor_prefix, horizontal_motor_prefix, *args, **kwargs):
        self.quadem_prefix = quadem_prefix
        self.vertical_motor_prefix = vertical_motor_prefix
        self.horizontal_motor_prefix = horizontal_motor_prefix

        super().__init__(*args, **kwargs)


class MyQuadEM(QuadEM):

    fast_current1 = Component(EpicsSignalRO, "Current1Ave")
    fast_current2 = Component(EpicsSignalRO, "Current2Ave")
    fast_current3 = Component(EpicsSignalRO, "Current3Ave")
    fast_current4 = Component(EpicsSignalRO, "Current4Ave")

    fast_position_x = Component(EpicsSignalRO, "PositionXAve")
    fast_position_y = Component(EpicsSignalRO, "PositionYAve")

    
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        for attr in self.component_names:
            if attr.startswith("fast_"):
                continue
            component = getattr(self, attr)
            component.kind = "omitted"

        #We will run it in continuous mode
        self.stage_sigs = {}

        self._status_type = Status

    
    def trigger(self):
        """
        We want to operate in continuous mode
        """
        if self._staged != Staged.yes:
            raise RuntimeError(
                "This detector is not ready to trigger."
                "Call the stage() method before triggering."
            )

        self._status = None
        self._status = self._status_type(self)
        self._status.set_finished()
        return self._status

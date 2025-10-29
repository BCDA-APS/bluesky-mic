from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor
from ophyd import EpicsSignalRO
from ophyd import FormattedComponent
from ophyd import QuadEM
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
    # _default_configuration_attrs = (
    #     'vert',
    #     'hor',
    #     )

    _default_read_attrs = (
        "vert",
        "hor",
        "current1",
        "current2",
        "current3",
        "current4",
        "x",
        "y",
    )

    vert = FormattedComponent(EpicsMotor, "{vertical_motor_prefix}")
    hor = FormattedComponent(EpicsMotor, "{horizontal_motor_prefix}")

    current1 = FormattedComponent(EpicsSignalRO, "{quadem_prefix}Current1Ave")
    current2 = FormattedComponent(EpicsSignalRO, "{quadem_prefix}Current2Ave")
    current3 = FormattedComponent(EpicsSignalRO, "{quadem_prefix}Current3Ave")
    current4 = FormattedComponent(EpicsSignalRO, "{quadem_prefix}Current4Ave")

    x = FormattedComponent(EpicsSignalRO, "{quadem_prefix}PositionXAve")
    y = FormattedComponent(EpicsSignalRO, "{quadem_prefix}PositionYAve")

    def __init__(
        self,
        quadem_prefix,
        vertical_motor_prefix,
        horizontal_motor_prefix,
        *args,
        **kwargs,
    ):
        self.quadem_prefix = quadem_prefix
        self.vertical_motor_prefix = vertical_motor_prefix
        self.horizontal_motor_prefix = horizontal_motor_prefix

        super().__init__(*args, **kwargs)


class MyQuadEM(QuadEM):
    current1 = Component(EpicsSignalRO, "Current1Ave")
    current2 = Component(EpicsSignalRO, "Current2Ave")
    current3 = Component(EpicsSignalRO, "Current3Ave")
    current4 = Component(EpicsSignalRO, "Current4Ave")

    x = Component(EpicsSignalRO, "PositionXAve")
    y = Component(EpicsSignalRO, "PositionYAve")

    _default_read_attrs = ("current1", "current2", "current3", "current4", "x", "y")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for attr in self.component_names:
            if attr.startswith("fast_"):
                continue
            component = getattr(self, attr)
            component.kind = "omitted"

        # We will run it in continuous mode
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

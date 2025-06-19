"""BDA device for slits in ISN."""

from ophyd import Device
from ophyd import EpicsMotor
from ophyd import FormattedComponent


class BDA(Device):
    """BDA device for slits.

    Attributes:
         low_slit: Low slit motor.
         high_slit: High slit motor.
         size: Slit size motor.
         center: Slit center motor.
    """

    def __init__(self, prefix, axis, **kwargs):
        """Initialize BDA device.

        Parameters:
            prefix (str): Device prefix.
            axis (str or int): Axis identifier.
            **kwargs: Additional arguments.
        """
        self.axis = axis
        super().__init__(prefix=prefix, **kwargs)

    low_slit = FormattedComponent(
        EpicsMotor, "{prefix}:Slit1{axis}xn", labels=("motors",), kind="config"
    )
    high_slit = FormattedComponent(
        EpicsMotor, "{prefix}:Slit1{axis}xp", labels=("motors",), kind="config"
    )
    size = FormattedComponent(
        EpicsMotor, "{prefix}:Slit1{axis}size", labels=("motors","baseline"),
          kind="config"
    )
    center = FormattedComponent(
        EpicsMotor, "{prefix}:Slit1{axis}center", labels=("motors","baseline"),
          kind="config"
    )

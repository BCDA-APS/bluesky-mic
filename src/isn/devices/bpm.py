from ophyd import QuadEM
from ophyd import EpicsSignalRO
from ophyd import Component
from ophyd import Device

from ophyd.device import Staged
from ophyd.status import Status


class BasicQuadEM(Device):

    """Temporary QuadEM implementation for the BPMs. The Sydor epics implementation 
    is still patchy, so it does not work properly with the QuadEM class."""

    fast_current1 = Component(EpicsSignalRO, "Current1Ave", kind="hinted")
    fast_current2 = Component(EpicsSignalRO, "Current2Ave", kind="hinted")
    fast_current3 = Component(EpicsSignalRO, "Current3Ave", kind="hinted")
    fast_current4 = Component(EpicsSignalRO, "Current4Ave", kind="hinted")

    fast_position_x = Component(EpicsSignalRO, "PositionXAve", kind="hinted")
    fast_position_y = Component(EpicsSignalRO, "PositionYAve", kind="hinted")
    

class MyQuadEM(QuadEM):

    fast_current1 = Component(EpicsSignalRO, "Current1Ave", kind="hinted")
    fast_current2 = Component(EpicsSignalRO, "Current2Ave", kind="hinted")
    fast_current3 = Component(EpicsSignalRO, "Current3Ave", kind="hinted")
    fast_current4 = Component(EpicsSignalRO, "Current4Ave", kind="hinted")

    fast_position_x = Component(EpicsSignalRO, "PositionXAve", kind="hinted")
    fast_position_y = Component(EpicsSignalRO, "PositionYAve", kind="hinted")

    
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

from apstools.devices.aps_cycle import ApsCycleDM
from apstools.devices import ApsMachineParametersDevice
from ophyd import Component

class PatchedApsCycleDM(ApsCycleDM):
    """BUGFIX for new fiscal year."""

    _cycle_ends = "2025-12-31 23:59:59"  # TODO: official date in 2026-01
    _cycle_name = "2025-3"  # TODO: apstools needs update

    def get(self):
        return self._cycle_name


class PatchedApsMachineParametersDevice(ApsMachineParametersDevice):
    """BUGFIX for new fiscal year."""
    aps_cycle = Component(PatchedApsCycleDM)
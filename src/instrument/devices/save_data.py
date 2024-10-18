__all__ = """
    savedata
""".split()

import logging

import bluesky.plan_stubs as bps
from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal

from ..utils.config_loaders import iconfig

logger = logging.getLogger(__name__)
logger.info(__file__)


class SaveData(Device):
    file_system = Component(EpicsSignal, "fileSystem", string=True)
    subdirectory = Component(EpicsSignal, "subDir", string=True)
    base_name = Component(
        EpicsSignal, "baseName", string=True
    )  # basename needs _ at teh end
    scanNumber = Component(EpicsSignal, "scanNumber")

    def setup_savedata(self, file_system, base_name, reset_counter=False):
        print("in setup_savedata function")
        # savedata.wait_for_connection()
        # yield from bps.mv(scaler1.preset_time, ct)  # counting time/point
        # yield from run_blocking_function(savedata.reset)
        yield from bps.sleep(0.2)  # arbitrary wait for EPICS to finish the reset.

        subdir = base_name
        if base_name[-1] == "_":
            subdir = base_name.strip("_")
        if base_name[-1] != "_":
            base_name = base_name + "_"
        if reset_counter:
            yield from bps.mv(self.scanNumber, 0)

        # caput(savedata.file_system.pvname, str(file_system))
        yield from bps.mv(
            self.file_system,
            file_system,
            self.subdirectory,
            f"/{subdir}/mda/",
            self.base_name,
            f"/{base_name}",
        )


pv = iconfig.get("DEVICES")["SAVE_DATA"]
savedata = SaveData(pv, name="savedata")

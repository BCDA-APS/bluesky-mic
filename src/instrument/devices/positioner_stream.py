"""
Positioner stream ophyd device class creation & instatiation
"""

import subprocess

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal

from ..user.misc import run_subprocess
from ..utils.config_loaders import iconfig


class PositionerStream(Device):
    """
    Positioner stream ophyd device class
    """

    reset_ = Component(EpicsSignal, "reset")
    start_ = Component(EpicsSignal, "start")
    stop_ = Component(EpicsSignal, "stop")
    status = Component(EpicsSignal, "status")
    outputFile = Component(EpicsSignal, "outputFile")

    def setup_positionstream(self, filename, filepath):
        """
        Setup positioner stream pv file name & path.
        """
        print("in setup_positionstream function")
        cmd = f'pvput -r "filePath" posvr:outputFile \'{{"filePath":"{filepath}"}}\''
        print(run_subprocess(cmd)[1])
        cmd = f'pvput -r "fileName" posvr:outputFile \'{{"fileName":"{filename}"}}\''
        print(run_subprocess(cmd)[1])

    def run_subprocess(self, command_list):
        """
        Run subprocess for positioner stream to get status output of commands
        """
        try:
            result = subprocess.getstatusoutput(command_list)
        except subprocess.CalledProcessError as e:
            result = e
            pass
        return result


pv = iconfig.get("DEVICES")["POSITION_STREAM"]
print(pv)
print(pv)
postrm = PositionerStream(pv, name="postrm")

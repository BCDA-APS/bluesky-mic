"""Positioner stream device module."""

import subprocess

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal

from ..utils.misc import run_subprocess


class PositionerStream(Device):
    """Device for positioner stream control."""

    reset_ = Component(EpicsSignal, "reset")
    start_ = Component(EpicsSignal, "start")
    stop_ = Component(EpicsSignal, "stop")
    status = Component(EpicsSignal, "status")
    outputFile = Component(EpicsSignal, "outputFile")

    def setup_positionstream(sefl, filename, filepath):
        """Set up positioner stream with filename and filepath."""
        print("in setup_positionstream function")
        cmd = f'pvput -r "filePath" posvr:outputFile \'{{"filePath":"{filepath}"}}\''
        print(run_subprocess(cmd)[1])
        cmd = f'pvput -r "fileName" posvr:outputFile \'{{"fileName":"{filename}"}}\''
        print(run_subprocess(cmd)[1])

    def run_subprocess(self, command_list):
        """Run a subprocess command.

        Parameters:
            command_list (str): Command to execute.

        Returns:
            tuple: Status and output of the command.
        """
        try:
            result = subprocess.getstatusoutput(command_list)
        except subprocess.CalledProcessError as e:
            result = e
            pass
        return result


# pv = iconfig.get("DEVICES")["POSITION_STREAM"]
# print(pv)
# print(pv)
# postrm = PositionerStream(pv, name="postrm")

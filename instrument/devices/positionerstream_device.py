"""SoftGlueZynq (FPGA)."""

import subprocess

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignal


def run_subprocess(command_list):
    try:
        result = subprocess.getstatusoutput(command_list)
    except subprocess.CalledProcessError as e:
        result = e
        pass
    return result


class PositionerStream(Device):
  reset_ = Component(EpicsSignal, 'reset')
  start_ = Component(EpicsSignal, 'start')
  stop_ = Component(EpicsSignal, 'stop')
  status = Component(EpicsSignal, 'status')
  outputFile = Component(EpicsSignal, 'outputFile')

  def setup_positionstream(self, filename, filepath):
    print("in setup_positionstream function")
    # TODO: refactor to use pvapy package - https://epics.anl.gov/extensions/pvaPy/production/index.html
    cmd = f"pvput -r \"filePath\" posvr:outputFile \'{{\"filePath\":\"{filepath}\"}}\'"
    print(run_subprocess(cmd)[1])
    cmd = f"pvput -r \"fileName\" posvr:outputFile \'{{\"fileName\":\"{filename}\"}}\'"
    print(run_subprocess(cmd)[1])
    print("exit setup_positionstream function")
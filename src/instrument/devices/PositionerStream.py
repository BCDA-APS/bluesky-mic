
__all__ = """
    postrm
    setup_positionstream
""".split()

from ophyd import Device, EpicsSignal, Component
from ..utils import run_subprocess

class PositionerStream(Device):
  reset_ = Component(EpicsSignal, 'reset')
  start_ = Component(EpicsSignal, 'start')
  stop_ = Component(EpicsSignal, 'stop')
  status = Component(EpicsSignal, 'status')
  outputFile = Component(EpicsSignal, 'outputFile')

def setup_positionstream(filename, filepath):
    print("in setup_positionstream function")
    cmd = f"pvput -r \"filePath\" posvr:outputFile \'{{\"filePath\":\"{filepath}\"}}\'"
    print(run_subprocess(cmd)[1])
    cmd = f"pvput -r \"fileName\" posvr:outputFile \'{{\"fileName\":\"{filename}\"}}\'"
    print(run_subprocess(cmd)[1])

def run_subprocess(command_list):
    try:
        result = subprocess.getstatusoutput(command_list)
    except subprocess.CalledProcessError as e:
        result = e
        pass
    return result



postrm = PositionerStream("posvr:", name="postrm")
import hklpy2
from ophyd import Component as Cpt
from ophyd import EpicsMotor
from ophyd import SoftPositioner

from .robot import RobotArmPositioner


class RobotArmDiffractometer(hklpy2.diffract.DiffractometerBase):
    """ISN Robot Arm as Diffractometer."""

    _real = "mu eta chi phi yaw pitch".split()

    h = Cpt(hklpy2.diffract.Hklpy2PseudoAxis, "", kind="hinted")
    k = Cpt(hklpy2.diffract.Hklpy2PseudoAxis, "", kind="hinted")
    l = Cpt(hklpy2.diffract.Hklpy2PseudoAxis, "", kind="hinted")

    # EPICS simulator PVs used, comments show beamline PVs to be used.
    mu = Cpt(EpicsMotor, "19idMMC:m4", kind="hinted")  # 19idMMC:m4
    eta = Cpt(SoftPositioner, kind="hinted", limits=(-180, 180), init_pos=0)
    chi = Cpt(SoftPositioner, kind="hinted", limits=(-180, 180), init_pos=0)
    phi = Cpt(SoftPositioner, kind="hinted", limits=(-180, 180), init_pos=0)
    yaw = Cpt(
        RobotArmPositioner,
        prefix="19IDRobot:",
        setpoint="Yaw",
        readback="Last_Position_Yaw",
        done="MC",
        execute="EXE",
        command="CMD",
    )
    pitch = Cpt(
        RobotArmPositioner,
        prefix="19IDRobot:",
        setpoint="Pitch",
        readback="Last_Position_Pitch",
        done="MC",
        execute="EXE",
        command="CMD",
    )

    radius = Cpt(
        RobotArmPositioner,
        prefix="19IDRobot:",
        setpoint="Radius",
        readback="Last_Position_R",
        done="MC",
        execute="EXE",
        command="CMD",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            solver="hkl_soleil",
            geometry="E6C",
            **kwargs,
        )
        # Can only set this _after_ device connects.
        # self.mode = "lifting_detector_mu"

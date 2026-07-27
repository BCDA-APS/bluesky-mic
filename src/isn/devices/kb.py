from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import FormattedComponent
from ophyd.status import AndStatus


class CapSensor(Device):
    pos = Component(EpicsSignalRO, "pos", name="pos")
    voltage = Component(EpicsSignalRO, "voltage", name="voltage")
    um_per_v = Component(EpicsSignalRO, "umPerV", name="um_per_v")
    offset = Component(EpicsSignal, "offset", name="offset")


class CapSensorMotor(EpicsMotor):
    cap_sensor = FormattedComponent(CapSensor, "{self._cap_sensor_pv}")

    def __init__(
        self,
        positioner_pv,
        cap_sensor_pv,
        coarse_pv=None,
        fine_pv=None,
        *args,
        **kwargs,
    ):
        self._cap_sensor_pv = cap_sensor_pv
        self._coarse_pv = coarse_pv
        self._fine_pv = fine_pv
        super().__init__(positioner_pv, *args, **kwargs)


class CapSensorMotorCoarse(CapSensorMotor):
    coarse = FormattedComponent(EpicsMotor, "{self._coarse_pv}")


class CapSensorMotorFine(CapSensorMotor):
    fine = FormattedComponent(EpicsMotor, "{self._fine_pv}")


class CapSensorMotorCoarseFine(CapSensorMotorCoarse, CapSensorMotorFine):
    pass


class VerticalKBAxis(Device):
    """Virtual positioner for KB vertical motion in um.

    Controls two motors (downstream and upstream) with configurable signs,
    enabling both differential (angle) and common-mode (translation) moves:

        ds_sign=+1, us_sign=-1  ->  differential: coarse/fine_vertical_angle_um
        ds_sign=+1, us_sign=+1  ->  common-mode:  coarse_y, fine_y

    WARNING — absolute move semantics
    ----------------------------------
    This device has no physical readback PV.  'position' is a software counter
    that starts at 0.0 when the session is initialised and is updated on every
    set() call.  As a consequence, bps.mv (absolute move) is only absolute
    relative to that software zero, NOT to any physical reference:

        bps.mv(kb.coarse_y, 5.0)   # first call  -> motors move +5 um
        bps.mv(kb.coarse_y, 5.0)   # second call -> motors do NOT move (already at 5.0)
        bps.mv(kb.coarse_y, 6.0)   # third call  -> motors move +1 um

    bps.mvr always behaves as expected regardless of the current position value.

    To redefine the reference point (e.g. after manually jogging the real
    motors, or to treat the current physical position as a new zero), call:

        kb.coarse_y.set_position(0.0)   # reset to zero
        kb.coarse_y.set_position(3.5)   # declare current position as 3.5 um

    This does NOT move any motor — it only updates the software counter.

    Parameters (passed through Component kwargs)
    -------------------------------------------
    ds_attr  : dotted attribute path on the parent KB device for the
               downstream motor, e.g. "y_ds.coarse" or "y_ds.fine"
    us_attr  : dotted attribute path for the upstream motor
    ds_sign  : sign applied to delta for the downstream motor (+1 or -1)
    us_sign  : sign applied to delta for the upstream motor (+1 or -1)
    """

    def __init__(self, prefix, *args, ds_attr, us_attr, ds_sign=1, us_sign=1, **kwargs):
        self._ds_attr = ds_attr
        self._us_attr = us_attr
        self._ds_sign = ds_sign
        self._us_sign = us_sign
        self._position = 0.0
        super().__init__(prefix, *args, **kwargs)

    def _resolve(self, attr_path):
        """Walk a dotted attribute path on the parent KB device."""
        obj = self.parent
        for attr in attr_path.split("."):
            obj = getattr(obj, attr)
        return obj

    @property
    def position(self):
        return self._position

    def set_position(self, value: float = 0.0):
        """Redefine the current software position without moving any motor.

        Use this to reset the reference after manual jogging or to establish
        a meaningful zero before running a scan with this axis.
        """
        self._position = float(value)

    def set(self, target):
        # target is an absolute position in the software coordinate.
        # bps.mv  passes target directly.
        # bps.mvr reads position and passes position+step as target,
        # so delta correctly equals step regardless of current position.
        delta = target - self._position
        ds = self._resolve(self._ds_attr)
        us = self._resolve(self._us_attr)
        # Update before issuing motor commands so post-move reads in mv_kb
        # see the new value immediately.
        self._position = target
        status_ds = ds.set(ds.user_readback.get() + self._ds_sign * delta)
        status_us = us.set(us.user_readback.get() + self._us_sign * delta)
        return AndStatus(status_ds, status_us)

    def stop(self, *, success=False):
        self._resolve(self._ds_attr).stop(success=success)
        self._resolve(self._us_attr).stop(success=success)


class KB(Device):
    _default_read_attrs = (
        "x",
        "y_ds",
        "y_us",
        "z",
        "theta_y",
        "theta_z",
        "vertical_angle",
        "vertical_average",
    )

    x = Component(
        CapSensorMotorCoarseFine,
        positioner_pv="19idKB:m18",
        cap_sensor_pv="19idKB:cap4:",
        coarse_pv="19idKB:m12",
        fine_pv="19idKB:m6",
        name="x",
    )

    y_ds = Component(
        CapSensorMotorCoarseFine,
        positioner_pv="19idKB:m16",
        cap_sensor_pv="19idKB:cap2:",
        coarse_pv="19idKB:m11",
        fine_pv="19idKB:m2",
        name="y_ds",
    )

    y_us = Component(
        CapSensorMotorCoarseFine,
        positioner_pv="19idKB:m15",
        cap_sensor_pv="19idKB:cap1:",
        coarse_pv="19idKB:m7",
        fine_pv="19idKB:m1",
        name="y_us",
    )

    z = Component(
        CapSensorMotorCoarseFine,
        positioner_pv="19idKB:m17",
        cap_sensor_pv="19idKB:cap3:",
        coarse_pv="19idKB:m8",
        fine_pv="19idKB:m5",
        name="z",
    )

    theta_y = Component(
        CapSensorMotorCoarseFine,
        positioner_pv="19idKB:SM1",
        cap_sensor_pv="19idKB:cap5:",
        coarse_pv="19idKB:m9",
        fine_pv="19idKB:m4",
        name="theta_y",
    )

    theta_z = Component(
        CapSensorMotorCoarse,
        positioner_pv="19idKB:SM2",
        cap_sensor_pv="19idKB:cap6:",
        coarse_pv="19idKB:m10",
        name="theta_z",
    )

    vertical_angle = Component(EpicsSignalRO, "vert:t2.C", name="vertical_angle_raw")
    vertical_average = Component(EpicsSignalRO, "vert:t2.D", name="vertical")

    coarse_vertical_angle_um = Component(
        VerticalKBAxis, "",
        ds_attr="y_ds.coarse", us_attr="y_us.coarse",
        ds_sign=1, us_sign=-1,
    )

    fine_vertical_angle_um = Component(
        VerticalKBAxis, "",
        ds_attr="y_ds.fine", us_attr="y_us.fine",
        ds_sign=1, us_sign=-1,
    )

    coarse_y = Component(
        VerticalKBAxis, "",
        ds_attr="y_ds.coarse", us_attr="y_us.coarse",
        ds_sign=1, us_sign=1,
    )

    fine_y = Component(
        VerticalKBAxis, "",
        ds_attr="y_ds.fine", us_attr="y_us.fine",
        ds_sign=1, us_sign=1,
    )


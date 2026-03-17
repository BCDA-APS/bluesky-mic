from ophyd import Component
from ophyd import Device
from ophyd import EpicsMotor
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import FormattedComponent


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
        name="x",
    )

    y_us = Component(
        CapSensorMotorCoarseFine,
        positioner_pv="19idKB:m15",
        cap_sensor_pv="19idKB:cap1:",
        coarse_pv="19idKB:m7",
        fine_pv="19idKB:m1",
        name="x",
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

    vertical_angle = Component(EpicsSignalRO, "vert:t2.C", name="vertical")
    vertical_average = Component(EpicsSignalRO, "vert:t2.D", name="vertical")


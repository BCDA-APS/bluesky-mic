from ophyd import FormattedComponent
from ophyd import EpicsMotor
from ophyd import EpicsSignal

from ophyd.areadetector import DetectorBase
from ophyd.areadetector import CamBase
from ophyd.areadetector import ROIPlugin
from ophyd.areadetector import StatsPlugin
from ophyd.areadetector import SingleTrigger
from ophyd.areadetector import ADComponent

from mic_common.devices.ad_fileplugin import MicHDF5

from bluesky.plan_stubs import mv


# class FlagCam(CamBase):

#     acquire_mode = ADComponent(EpicsSignal, "ImageMode")

class FlagStatsPlugin(StatsPlugin):

    _default_read_attrs = ("total",)

class Flag(SingleTrigger, DetectorBase):

    _default_configuration_attrs = ()

    _default_read_attrs =(
        "stats1",
    )

    motor = FormattedComponent(EpicsMotor, "{motor_prefix}")
    cam = FormattedComponent(CamBase, "{flag_prefix}"+"cam1:")
    hdf1 = FormattedComponent(MicHDF5, "{flag_prefix}"+"HDF1:")

    roi1 = FormattedComponent(ROIPlugin, "{flag_prefix}"+"ROI1:")
    roi2 = FormattedComponent(ROIPlugin, "{flag_prefix}"+"ROI2:")
    roi3 = FormattedComponent(ROIPlugin, "{flag_prefix}"+"ROI3:")
    roi4 = FormattedComponent(ROIPlugin, "{flag_prefix}"+"ROI4:")

    stats1 = FormattedComponent(FlagStatsPlugin, "{flag_prefix}"+"Stats1:")
    stats2 = FormattedComponent(FlagStatsPlugin, "{flag_prefix}"+"Stats2:")
    stats3 = FormattedComponent(FlagStatsPlugin, "{flag_prefix}"+"Stats3:")
    stats4 = FormattedComponent(FlagStatsPlugin, "{flag_prefix}"+"Stats4:")

    stats1.read_attrs = ("total",)


    def __init__(self, flag_prefix, motor_prefix, in_position, out_position, *args, **kwargs):
        self.flag_prefix = flag_prefix
        self.motor_prefix = motor_prefix
        self._in_position = in_position
        self._out_position = out_position
        super().__init__(*args, **kwargs)
        self.cam.stage_sigs["image_mode"] = 0
        self.cam.stage_sigs["num_images"] = 1

        


    def on(self):
        self.cam.acquire.put(1)

    def off(self):
        self.cam.acquire.put(0)

    def move_in(self):
        yield from mv(self.motor, self._in_position)

    def move_out(self):
        yield from mv(self.motor, self._out_position)

    def set_in_position(self, new_in_position=None):
        if not new_in_position:
            new_in_position = self.motor.user_readback.get()

        self._in_position = new_in_position

    def set_out_position(self, new_out_position=None):
        if not new_out_position:
            new_out_position = self.motor.user_readback.get()

        self._out_position = new_out_position
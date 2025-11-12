from bluesky.plan_stubs import mv
from mic_common.devices.ad_fileplugin import MicHDF5
from ophyd import EpicsMotor
from ophyd import FormattedComponent
from ophyd.areadetector import CamBase
from ophyd.areadetector import SingleTrigger
from ophyd.areadetector import DetectorBase
from ophyd.areadetector import ROIPlugin
from ophyd.areadetector import StatsPlugin
from ophyd.areadetector import TIFFPlugin



class Flag(DetectorBase):
    _default_configuration_attrs = ()

    motor = FormattedComponent(EpicsMotor, "{motor_prefix}")
    cam = FormattedComponent(CamBase, "{flag_prefix}" + "cam1:")
    hdf1 = FormattedComponent(MicHDF5, "{flag_prefix}" + "HDF1:")
    tiff1 = FormattedComponent(TIFFPlugin, "{flag_prefix}" + "TIFF1:")

    roi1 = FormattedComponent(ROIPlugin, "{flag_prefix}" + "ROI1:")
    roi2 = FormattedComponent(ROIPlugin, "{flag_prefix}" + "ROI2:")
    roi3 = FormattedComponent(ROIPlugin, "{flag_prefix}" + "ROI3:")
    roi4 = FormattedComponent(ROIPlugin, "{flag_prefix}" + "ROI4:")

    stats1 = FormattedComponent(StatsPlugin, "{flag_prefix}" + "Stats1:")
    stats2 = FormattedComponent(StatsPlugin, "{flag_prefix}" + "Stats2:")
    stats3 = FormattedComponent(StatsPlugin, "{flag_prefix}" + "Stats3:")
    stats4 = FormattedComponent(StatsPlugin, "{flag_prefix}" + "Stats4:")

    def __init__(
        self, flag_prefix, motor_prefix, in_position, out_position, *args, **kwargs
    ):
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

    def save_tiff_images_on(self):
        self.tiff1.stage_sigs["enable"] = 1
        self.tiff1.stage_sigs["auto_save"] = 1

    def save_tiff_images_off(self):
        self.tiff1.stage_sigs["enable"] = 0
        self.tiff1.stage_sigs["auto_save"] = 0

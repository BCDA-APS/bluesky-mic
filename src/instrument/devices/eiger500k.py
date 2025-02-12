

from ophyd import EigerDetectorCam
from .utils import mode_setter, value_setter


class Eiger500k(EigerDetectorCam):
    
    file_writer_enable = Component(EpicsSignal, ".FWEnable")
    file_compression = Component(EpicsSignal, ".FWCompression")
    num_images_per_file = Component(EpicsSignal, ".FWNImagesPerFile")
    file_name_pattern = Component(EpicsSignal, ".FWNamePattern")
    save_files = Component(EpicsSignal, ".SaveFiles")

    def setup_external_enable_trigger(self):

    def set_trigger_mode(self, mode):
        pass

    @value_setter("acquire_period")
    def set_acquire_period(self, value):
        pass

    @value_setter("acquire_time")
    def set_acquire_time(self, value):
        pass





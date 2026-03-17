from apstools.devices import LabJackT8

class IsnLabJackT8(LabJackT8):
    _default_read_attrs = ['analog_inputs']
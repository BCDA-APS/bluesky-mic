from ophyd import Device

from apsbits.core.instrument_init import oregistry


class FastShutter(Device):

    def open(self):
        sg = oregistry['softglue'] if "FAST_SHUTTER" in oregistry['softglue'].det_keymap else oregistry['softglue2']
        fs = getattr(sg, f'io.fo{sg.det_keymap["FAST_SHUTTER"]}')
        fs.put("1")

    def close(self):
        sg = oregistry['softglue'] if "FAST_SHUTTER" in oregistry['softglue'].det_keymap else oregistry['softglue2']
        fs = getattr(sg, f'io.fo{sg.det_keymap["FAST_SHUTTER"]}')
        fs.put("0")

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def __init__(self, prefix, **kwargs):
        super().__init__(prefix, **kwargs)
        self._enabled = True
    

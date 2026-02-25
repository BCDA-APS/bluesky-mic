from apsbits.core.instrument_init import oregistry


## Get the current working directory for the savedata
def get_save_data_path():
    savedata = oregistry.find("savedata", allow_none=True)
    if savedata is None:
        return None
    return savedata.get_auto_storage_path()

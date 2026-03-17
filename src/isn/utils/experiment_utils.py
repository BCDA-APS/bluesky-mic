
from pathlib import Path

from apsbits.core.instrument_init import oregistry

from isn.utils.run_engine import RE
from mic_common.utils.dm_utils import dm_get_experiment_data_path

from mictools.config import set_path

savedata = oregistry.find("savedata", allow_none=True)

def create_subdirectory_str(experiment_path: Path):
    # Get the last two parts of the path
    parts = experiment_path.parts[4:]
    # Join them with an underscore
    subdirectory = "/".join(parts)
    return subdirectory

def get_last_scan_number(experiment_path: Path):
    # Load list of files in the experiment directory
    files = list(experiment_path.glob("*.h5"))
    # Extract scan numbers from file names assuming they are in the format "Scan_XXXX.h5"
    scan_numbers = []
    for file in files:
        scanno = str(file).split(".")[0][-4:]
        scan_numbers.append(int(scanno))

    return max(scan_numbers) if scan_numbers else 0
    

def load_experiment(experiment_name=None):
    """
    Loads an experiment from the DM. If not provided, it will load the experiment defined
    in the savedata device.
    """
    print("Loading experiment")

    if experiment_name is None:
        
        print(savedata.full_path_name.get())
        if savedata is None:
            raise ValueError(
                "No experiment name provided and no savedata device found."
            )
        experiment_path = Path(savedata.full_path_name.get())
        # scan_number = savedata.next_scan_number.get()
        # RE.md['scan_id'] = scan_number

    else:
        experiment_path = dm_get_experiment_data_path(experiment_name)
        subdirectory = create_subdirectory_str(experiment_path)
        savedata.file_system.set("/gdata/dm/19ID")
        savedata.subdirectory.set(subdirectory)

    scan_number = get_last_scan_number(experiment_path)
    savedata.next_scan_number.set(scan_number)
    RE.md['scan_id'] = scan_number

        #Now we check which scan number we are on

    set_path(str(experiment_path))

    

    
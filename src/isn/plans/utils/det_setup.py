"""
A collection of functions to setup the detectors.

@author: yluo(grace227)

"""

from apsbits.utils.controls_setup import oregistry
from apsbits.utils.config_loaders import get_config

savedata = oregistry["savedata"]
xrf_me7 = oregistry["xrf_me7"]
xrf_me7_hdf = oregistry["xrf_me7_hdf"]
ptycho = oregistry["ptycho"]
ptycho_hdf = oregistry["ptycho_hdf"]

iconfig = get_config()
netcdf_delimiter = iconfig.get("FILE_DELIMITER")
xrf_me7_folder = iconfig.get("XRF_ME7_FOLDER")
ptycho_folder = iconfig.get("PTYCHO_FOLDER")


def xrf_me7_setup(num_capture, dwell, filename):
    """
    Setup the xrf_me7 detector.

    Parameters
    ----------
    num_capture : int
        The number of images to capture.
    dwell : float
        The exposure time for the xrf_me7 detector.
    filename : str
        The filename to save the xrf_me7 data.

    """
    yield from xrf_me7.scan_init(exposure_time=dwell, num_images=num_capture)
    yield from xrf_me7_hdf.setup_file_writer(
        savedata, 
        xrf_me7_folder, 
        num_capture, 
        filename=filename, 
        beamline_delimiter=netcdf_delimiter,
    )


def ptycho_setup(trigger_mode, num_capture, dwell, ptycho_exp_factor, filename):
    """
    Setup the ptycho detector.

    Parameters
    ----------
    num_capture : int
        The number of images to capture.
    dwell : float
        The exposure time for the ptycho detector.
    ptycho_exp_factor : float
        The exposure factor for the ptycho measurement.
    filename : str
        The filename to save the ptycho data.

    """
    # yield from cam.set_trigger_mode("Internal Enable")
    yield from ptycho.set_acquire("DONE")
    yield from ptycho.set_trigger_mode(trigger_mode)
    yield from ptycho.scan_init(exposure_time=dwell, num_images=num_capture, 
                                ptycho_exp_factor=ptycho_exp_factor)
    yield from ptycho.set_acquire("Acquiring")
    yield from ptycho.set_file_writer_enable("Disable")
    yield from ptycho_hdf.set_capture("DONE")
    yield from ptycho_hdf.setup_file_writer(
        savedata, 
        ptycho_folder, 
        num_capture, 
        filename=filename, 
        beamline_delimiter=netcdf_delimiter,
    )
    yield from ptycho_hdf.set_capture("Capturing")
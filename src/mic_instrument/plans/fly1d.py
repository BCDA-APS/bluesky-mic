"""
Creating a bluesky plan that interacts with Scan Record.

@author: yluo(grace227)

EXAMPLE::

    # Load this code in IPython or Jupyter notebook:
    %run -i user/fly2d_2idsft.py

    # # Run the plan with the RunEngine:
    # RE(scan_record2(scanrecord_name = 'scan1', ioc = "2idsft:", m1_name = 'm1',
    #                m1_start = -0.5, m1_finish = 0.5,
    #                m2_name = 'm3', m2_start = -0.2 ,m2_finish = 0.2,
    #                npts = 50, dwell_time = 0.1))

"""

from typing import Any
from typing import Dict
from typing import Generator
from typing import Optional

__all__ = """
    fly1d
""".split()

import logging
import os

from ..configs.device_config_19id import savedata
from ..configs.device_config_19id import scan1
from ..configs.device_config_19id import xrf_me7
from ..configs.device_config_19id import xrf_me7_hdf

logger = logging.getLogger(__name__)
logger.info(__file__)
SCAN_OVERHEAD = 0.3

print("Creating RE plan that uses scan record to do 1D fly scan")
print("Getting list of avaliable detectors")


det_name_mapping: Dict[str, Dict[str, Any]] = {
    "simdet": {"cam": None, "hdf": None},
    "xrf_me7": {"cam": xrf_me7, "hdf": xrf_me7_hdf},
    "preamp": {"cam": None, "hdf": None},
    "fpga": {"cam": None, "hdf": None},
    "ptycho": {"cam": None, "hdf": None},
}


def selected_dets(**kwargs: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Select detectors based on provided keyword arguments.

    Parameters
    ----------
    **kwargs : Dict[str, Any]
        Keyword arguments where keys ending in '_on' indicate detector selection.

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Dictionary of selected detectors with their configurations.
    """
    dets = {}
    rm_str = "_on"
    for k, v in kwargs.items():
        if all([v, isinstance(v, bool), rm_str in k]):
            det_str = k[: -len(rm_str)]
            dets.update({det_str: det_name_mapping[det_str]})
    return dets


def fly1d(
    samplename: str = "smp1",
    user_comments: str = "",
    width: float = 0,
    x_center: Optional[float] = None,
    stepsize_x: float = 0,
    dwell: float = 0,
    smp_theta: Optional[float] = None,
    simdet_on: bool = False,
    xrf_me7_on: bool = True,
    ptycho_on: bool = False,
    preamp_on: bool = False,
    fpga_on: bool = False,
    position_stream: bool = False,
    wf_run: bool = False,
    analysisMachine: str = "mona2",
    eta: float = 0,
) -> Generator[Any, None, None]:
    """
    Execute a 1D fly scan using the scan record.

    Parameters
    ----------
    samplename : str, optional
        Name of the sample, defaults to "smp1"
    user_comments : str, optional
        User comments for the scan
    width : float, optional
        Width of the scan in motor units
    x_center : float, optional
        Center position of the scan
    stepsize_x : float, optional
        Step size in motor units
    dwell : float, optional
        Dwell time per point in seconds
    smp_theta : float, optional
        Sample theta angle
    simdet_on : bool, optional
        Enable simulated detector
    xrf_me7_on : bool, optional
        Enable XRF ME7 detector
    ptycho_on : bool, optional
        Enable ptychography detector
    preamp_on : bool, optional
        Enable preamp detector
    fpga_on : bool, optional
        Enable FPGA detector
    position_stream : bool, optional
        Enable position streaming
    wf_run : bool, optional
        Enable workflow run
    analysisMachine : str, optional
        Analysis machine name, defaults to "mona2"
    eta : float, optional
        Estimated time of arrival

    Yields
    ------
    Generator[Any, None, None]
        Bluesky plan messages
    """
    ##TODO Close shutter while setting up scan parameters

    print(f"Using {scan1.prefix} as the outter scanRecord")
    if scan1.connected:
        logger.info(f"{scan1.prefix} is connected")

        """Set up scan parameters and get estimated time of a scan"""
        yield from scan1.set_center_width_stepsize(x_center, width, stepsize_x)
        numpts_x = scan1.number_points.value
        eta = numpts_x * dwell * (1 + SCAN_OVERHEAD)
        logger.info(f"Number_points in X: {numpts_x}")
        logger.info(f"Estimated_time for this scan is {eta}")

        """Check which detectors to trigger"""
        logger.info("Determining which detectors are selected")
        dets = selected_dets(**locals())

        ##TODO Create folder for the desire file/data structure
        basepath = savedata.get().file_system
        for det_name, det_var in dets.items():
            det_path = os.path.join(basepath, det_name)
            logger.info(f"Setting up {det_name} to have data saved at {det_path}")
            hdf = det_var["hdf"]
            if hdf is not None:
                hdf.set_filepath(det_path)

        def watch_execute_scan(old_value: int, value: int, **kwargs: Any) -> None:
            """
            Callback function to monitor scan execution status.
            """
            pass

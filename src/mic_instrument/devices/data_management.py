# from ..utils import logger
import logging

from apstools.devices import DM_WorkflowConnector
from apstools.utils import dm_api_proc
from apstools.utils.aps_data_management import dm_setup
from ophyd import Signal

from mic_instrument.utils.config_loaders import iconfig

logger = logging.getLogger(__name__)
logger.info(__file__)

__all__ = """
    dm_experiment
    dm_workflow
""".split()

dm_setup(iconfig["DM_SETUP_FILE"])
api = dm_api_proc()
dm_workflow = DM_WorkflowConnector(name="dm_workflow", labels=("dm",))
dm_workflow.owner.put(dm_api_proc().username)

# TODO: make this an EpicsSignal instead
dm_experiment = Signal(name="dm_experiment", value="", labels=("dm",))

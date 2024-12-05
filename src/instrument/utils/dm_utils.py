"""
Setup new user in Bluesky.
"""

from apstools.utils import dm_api_ds, dm_api_proc, dm_api_daq
from apstools.utils.aps_data_management import (
    DEFAULT_UPLOAD_TIMEOUT, DEFAULT_UPLOAD_POLL_PERIOD
)

from dm import (
    EsafApsDbApi, BssApsDbApi, ExperimentDsApi, UserDsApi, ObjectAlreadyExists
)
from datetime import datetime
from numpy import unique
from pathlib import Path
from time import time
from bluesky.plan_stubs import sleep, null
from ..devices.data_management import dm_workflow
from ._logging_setup import logger
logger.info(__file__)

__all__ = """
    dm_get_experiment_data_path
    dm_upload
    dm_upload_info
""".split()

esaf_api = EsafApsDbApi()
bss_api = BssApsDbApi()
exp_api = ExperimentDsApi()
user_api = UserDsApi()

DEFAULT_USERS = [
    "d284110",  # yluo
]


def dm_get_experiment_data_path(dm_experiment_name: str):
    return Path(dm_api_ds().getExperimentByName(dm_experiment_name)["dataDirectory"])


def get_processing_job_status(id=None, owner="user4idd"):
    if id is None:
        id = dm_workflow.job_id.get()
    return dm_api_proc().getProcessingJobById(id=id, owner=owner)


def dm_upload(experiment_name, folder_path, **daqInfo):
    return dm_api_daq().upload(
        experiment_name, folder_path, daqInfo
    )


def dm_upload_info(id):
    return dm_api_daq().getUploadInfo(id)


def dm_upload_wait(
    id,
    timeout: float = DEFAULT_UPLOAD_TIMEOUT,
    poll_period: float = DEFAULT_UPLOAD_POLL_PERIOD,
):
    """
    (bluesky plan) Wait for APS DM data acquisition to upload a file.

    PARAMETERS

    - Experiment id
    - timeout *float*: Number of seconds to wait before raising a 'TimeoutError'.
    - poll_period *float*: Number of seconds to wait before check DM again.

    RAISES

    - TimeoutError: if DM does not identify file within 'timeout' (seconds).

    """

    t0 = time()
    deadline = t0 + timeout
    yield from null()  # now, it's a bluesky plan

    while time() <= deadline:
        if dm_upload_info(id)["status"].lower() != "done":
            yield from sleep(poll_period)
        else:
            return

    raise TimeoutError(
        f"DM upload timed out after {time()-t0 :.1f} s."
    )


def list_esafs(year=datetime.now().year, sector="04"):
    return esaf_api.listEsafs(sector, year)


def get_esaf_info(id):
    return esaf_api.getEsaf(id)


def get_esaf_users_badge(id):
    info = get_esaf_info(id)
    badges = []
    for user in info["experimentUsers"]:
        badges.append(user["badge"])
    return badges


def get_current_run():
    return bss_api.getCurrentRun()


def dm_experiment_setup(
    experiment_name, esaf_id=None, users_name_list: list = [], **kwargs
):
    # Gets the users from the ESAF.
    if esaf_id is not None:
        badges = get_esaf_users_badge(esaf_id)
        _users = []
        for b in badges:
            _users.append(f"d{b}")
        users_name_list = list(users_name_list) + _users

    # TODO: if no dates are passed, it will automatically make it from now to
    # the end of the current run. Is it better to just tie it to the ESAF?
    if kwargs.get("startDate", None) is None:
        kwargs["startDate"] = datetime.now().strftime("%d-%b-%y")
    if kwargs.get("endDate", None) is None:
        kwargs["endDate"] = datetime.fromisoformat(
            get_current_run()["endTime"]
        ).strftime("%d-%b-%y")

    exp = create_dm_experiment(experiment_name, **kwargs)
    users = add_dm_users(experiment_name, users_name_list)
    return exp, users


def create_dm_experiment(
    experiment_name, description="", rootPath=None, startDate=None, endDate=None
):
    if rootPath is None:
        rootPath = get_current_run()["name"]
    return exp_api.addExperiment(
        experiment_name,
        typeName="4IDD",
        description=description,
        rootPath=rootPath,
        startDate=startDate,
        endDate=endDate
    )


def add_dm_users(experiment_name, users_name_list):
    ulist = unique(DEFAULT_USERS + list(users_name_list))
    output = []
    for user in ulist:
        try:
            output.append(user_api.addUserExperimentRole(
                username=user, roleName="User", experimentName=experiment_name
            ))
        except ObjectAlreadyExists:
            pass
    return output


def get_experiment(experiment_name):
    return exp_api.getExperimentByName(experiment_name)


def get_experiments_names(since="2018-01-01", until="2100-01-01"):
    exps = exp_api.getExperimentsByStation("4IDD")[::-1]
    names = []
    for exp in exps:
        _start = datetime.fromisoformat(exp["startDate"]).utctimetuple()
        _low_lim = datetime.fromisoformat(since).utctimetuple()
        _high_lim = datetime.fromisoformat(until).utctimetuple()
        if (_start >= _low_lim) & (_start <= _high_lim):
            names.append(exp["name"])
    return names


def current_run_experiments_names():
    _run = get_current_run()
    return get_experiments_names(since=_run["startTime"], until=_run["endTime"])


def get_proposal_info(proposal_id: int, run: str = None):
    if run is None:
        run = get_current_run()["name"]
    return bss_api.getProposal(proposal_id, run)


def list_proposals(run: str = None):
    if run is None:
        run = get_current_run()["name"]
    return bss_api.listProposals(run)
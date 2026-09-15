"""Client wrapper for APS Data Management workflow processing."""

import logging
import os
from collections.abc import Callable
from typing import Any

from dm import DmException
from dm import ObjectAlreadyExists
from dm.common.utility.configurationManager import ConfigurationManager
from dm.proc_web_service.api.workflowProcApi import WorkflowProcApi

logger = logging.getLogger(__name__)

_DM_AGENT: "DMAgent | None" = None


def _restore_root_logging(level: int, handlers: list[logging.Handler]) -> None:
    root_logger = logging.getLogger()
    original_handler_ids = {id(handler) for handler in handlers}

    for handler in list(root_logger.handlers):
        if id(handler) not in original_handler_ids:
            root_logger.removeHandler(handler)

    root_logger.setLevel(level)


def _call_preserving_root_logging(
    function: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Call DM APIs without letting them replace Bluesky logging settings."""
    root_logger = logging.getLogger()
    root_level = root_logger.level
    root_handlers = list(root_logger.handlers)

    try:
        return function(*args, **kwargs)
    finally:
        _restore_root_logging(root_level, root_handlers)


def _to_dict(dm_object: Any) -> dict[str, Any]:
    """Return a plain dict from a DM object or mapping."""
    if hasattr(dm_object, "getDictRep"):
        return dm_object.getDictRep(keyList="ALL")
    return dict(dm_object)


def _normalize_esaf_id(esaf_id: int | str | None) -> int | None:
    if esaf_id is None:
        return None
    if isinstance(esaf_id, str) and not esaf_id.strip():
        return None
    return int(esaf_id)


class DMAgent:
    """Session-scoped client for APS DM workflows, experiments, and DAQs."""

    def __init__(self):
        """Create a DM workflow processing API client from the configured login."""
        self.workflow_args: dict[str, dict[str, Any]] = {}
        self.experiment_type_name: str | None = None
        self.config_manager = _call_preserving_root_logging(
            ConfigurationManager.getInstance
        )
        self.dm_user, password = _call_preserving_root_logging(
            self.config_manager.parseLoginFile
        )
        self._dm_password = password
        proc_service_url = _call_preserving_root_logging(
            self.config_manager.getProcWebServiceUrl
        )
        self.workflow_api = _call_preserving_root_logging(
            WorkflowProcApi,
            self.dm_user,
            password,
            proc_service_url,
        )

    def _call_preserving_root_logging(
        self,
        function: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Call DM APIs without letting them replace Bluesky logging settings."""
        return _call_preserving_root_logging(function, *args, **kwargs)

    def set_workflow_args(self, name: str, args: dict[str, Any]) -> None:
        """Store default argument values for a workflow alias."""
        self.workflow_args[name] = dict(args)

    def set_experiment_type_name(self, type_name: str) -> None:
        """Store the default DM experiment type name for this session."""
        if not isinstance(type_name, str) or not type_name.strip():
            raise ValueError("DM experiment type name must be a non-empty string.")
        self.experiment_type_name = type_name

    def _get_station_name(self, station_name: str | None = None) -> str:
        station_name = station_name or os.environ.get("DM_STATION_NAME")
        if not isinstance(station_name, str) or not station_name.strip():
            raise ValueError(
                "DM station name is required. Pass station_name or configure "
                "DM_STATION_NAME during startup."
            )
        return station_name

    def _get_esaf_info(
        self,
        esaf_id: int | str,
        station_name: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        from dm import EsafApsDbApi
        from dm.common.constants.dmExperimentConstants import DM_EXPERIMENT_USERS_KEY

        aps_db_service_url = self._call_preserving_root_logging(
            self.config_manager.getApsDbWebServiceUrl
        )
        esaf_api = self._call_preserving_root_logging(
            EsafApsDbApi,
            self.dm_user,
            self._dm_password,
            aps_db_service_url,
        )
        esaf = self._call_preserving_root_logging(
            esaf_api.getStationEsafById,
            station_name,
            int(esaf_id),
        )
        esaf_info = _to_dict(esaf)
        return esaf_info, list(esaf_info.get(DM_EXPERIMENT_USERS_KEY, []))

    def _add_experiment_users_from_esaf(
        self,
        *,
        experiment_name: str,
        station_name: str,
        experimenters: list[dict[str, Any]],
    ) -> dict[str, list[str]]:
        from dm import ObjectNotFound
        from dm import UserDsApi
        from dm.common.constants import dmRole
        from dm.common.constants.dmObjectLabels import DM_Y_KEY
        from dm.common.constants.dmUserConstants import DM_BADGE_KEY
        from dm.common.constants.dmUserConstants import DM_PI_FLAG_KEY

        ds_service_url = self._call_preserving_root_logging(
            self.config_manager.getDsWebServiceUrl
        )
        user_api = self._call_preserving_root_logging(
            UserDsApi,
            self.dm_user,
            self._dm_password,
            ds_service_url,
        )
        linked_users: dict[str, list[str]] = {"pis": [], "users": [], "skipped": []}

        for experimenter in experimenters:
            badge = experimenter.get(DM_BADGE_KEY)
            try:
                username = f"d{int(badge)}"
            except (TypeError, ValueError):
                linked_users["skipped"].append(str(badge))
                continue

            pi_flag = str(experimenter.get(DM_PI_FLAG_KEY, ""))
            if pi_flag.startswith(DM_Y_KEY):
                role_name = dmRole.DM_PI_EXPERIMENT_ROLE
                role_key = "pis"
            else:
                role_name = dmRole.DM_USER_EXPERIMENT_ROLE
                role_key = "users"

            try:
                self._call_preserving_root_logging(
                    user_api.getUserByUsername,
                    username,
                )
                self._call_preserving_root_logging(
                    user_api.addUserExperimentRole,
                    username,
                    role_name,
                    experiment_name,
                    station_name,
                )
            except ObjectAlreadyExists:
                pass
            except ObjectNotFound:
                logger.warning("DM user %s from ESAF was not found; skipping", username)
                linked_users["skipped"].append(username)
                continue
            linked_users[role_key].append(username)

        return linked_users

    def get_workflow_args(self, name: str) -> dict[str, Any]:
        """Return default argument values for a workflow alias."""
        try:
            return self.workflow_args[name]
        except KeyError as exc:
            raise KeyError(f"No DM workflow args configured for {name!r}") from exc

    def get_workflow_arguments(self, workflow_name: str) -> dict[str, Any]:
        """Return the arguments schema of a registered workflow."""
        try:
            wf_obj = self._call_preserving_root_logging(
                self.workflow_api.getWorkflowByName,
                self.dm_user,
                workflow_name,
            )
            return wf_obj.getDictRep(keyList="ALL").get("arguments", {})
        except DmException as e:
            logger.warning(
                f"Could not fetch argument schema for workflow {workflow_name}: {e}"
            )
            return {}

    def validate_args(self, workflow_name: str, args: dict[str, Any]) -> None:
        """Validate args against the registered workflow schema."""
        schema = self.get_workflow_arguments(workflow_name)
        if not schema:
            logger.warning(
                f"No argument schema available for workflow {workflow_name}; "
                "skipping validation."
            )
            return

        problems: list[str] = []

        unknown = sorted(set(args) - set(schema))
        if unknown:
            problems.append(f"unknown args: {unknown}")

        missing = sorted(
            k for k, spec in schema.items() if spec.get("required") and k not in args
        )
        if missing:
            problems.append(f"missing required args: {missing}")

        for key, value in args.items():
            spec = schema.get(key)
            if not spec:
                continue
            choices = spec.get("choices")
            if not choices:
                continue
            allowed = {str(c) for c in choices}
            arg_type = spec.get("type")
            if arg_type == "multiple_choice":
                tokens = [t.strip() for t in str(value).split(",") if t.strip() != ""]
                bad = [t for t in tokens if t not in allowed]
                if bad:
                    problems.append(f"{key}={value!r}: {bad} not in choices {choices}")
            elif str(value) not in allowed:
                problems.append(f"{key}={value!r} not in choices {choices}")

        if problems:
            raise ValueError(
                f"Invalid args for workflow '{workflow_name}': " + "; ".join(problems)
            )

    def start_processing_job(
        self, workflow_name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Start a processing job for a workflow with given args."""
        job = {}
        self.validate_args(workflow_name, args)
        try:
            job_obj = self._call_preserving_root_logging(
                self.workflow_api.startProcessingJob,
                self.dm_user,
                workflow_name,
                args,
            )
            job = job_obj.getDictRep(keyList="ALL")
        except DmException as e:
            logger.error(
                f"ERROR: Unable to start processing job for workflow {workflow_name}"
            )
            logger.error(e)
        return job

    def get_processing_job(self, job_id: str) -> dict[str, Any]:
        """Get processing job metadata by job ID."""
        job = {}
        try:
            job_obj = self._call_preserving_root_logging(
                self.workflow_api.getProcessingJobById,
                owner=self.dm_user,
                id=job_id,
            )
            job = job_obj.getDictRep(keyList="ALL")
        except DmException as e:
            logger.error(f"ERROR: Unable to fetch processing job {job_id}")
            logger.error(e)
        return job

    def get_experiment(self, experiment_name: str) -> dict[str, Any]:
        """Get experiment metadata by DM experiment name."""
        from apstools.utils import dm_api_ds

        ds_api = self._call_preserving_root_logging(dm_api_ds)
        experiment = self._call_preserving_root_logging(
            ds_api.getExperimentByName,
            experiment_name,
        )
        return _to_dict(experiment)

    def create_experiment(
        self,
        experiment_name: str,
        type_name: str | None = None,
        *,
        station_name: str | None = None,
        description: str | None = None,
        root_path: str | None = None,
        storage_name: str | None = None,
        globus_group_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        managed_directory_structure: bool | None = None,
        beamline_user_account: str | None = None,
        beamline_admin_account: str | None = None,
        esaf_id: int | str | None = None,
        ignore_existing: bool = True,
    ) -> dict[str, Any]:
        """Create/register a DM experiment and return its metadata."""
        from apstools.utils import dm_api_ds
        from dm.common.constants.dmEsafConstants import DM_ESAF_TITLE_KEY

        if type_name is None:
            type_name = self.experiment_type_name
        if not isinstance(type_name, str) or not type_name.strip():
            raise ValueError(
                "DM experiment type name is required. Pass type_name or configure "
                "DMAgent.experiment_type_name during startup."
            )

        normalized_esaf_id = _normalize_esaf_id(esaf_id)
        esaf_info: dict[str, Any] | None = None
        esaf_experimenters: list[dict[str, Any]] = []
        if normalized_esaf_id is not None:
            station_name = self._get_station_name(station_name)
            esaf_info, esaf_experimenters = self._get_esaf_info(
                normalized_esaf_id,
                station_name,
            )
            if description is None:
                esaf_title = esaf_info.get(DM_ESAF_TITLE_KEY, "")
                description = f"{esaf_title} (ESAF id: {normalized_esaf_id})"

        ds_api = self._call_preserving_root_logging(dm_api_ds)
        try:
            experiment = self._call_preserving_root_logging(
                ds_api.addExperiment,
                experimentName=experiment_name,
                stationName=station_name,
                typeName=type_name,
                description=description,
                rootPath=root_path,
                storageName=storage_name,
                globusGroupId=globus_group_id,
                startDate=start_date,
                endDate=end_date,
                managedDirectoryStructure=managed_directory_structure,
                beamlineUserAccount=beamline_user_account,
                beamlineAdminAccount=beamline_admin_account,
            )
        except ObjectAlreadyExists:
            if not ignore_existing:
                raise
            logger.info("DM experiment %s already exists", experiment_name)
            experiment_info = self.get_experiment(experiment_name)
        else:
            experiment_info = _to_dict(experiment)

        if normalized_esaf_id is not None:
            experiment_info["linked_esaf_id"] = normalized_esaf_id
            experiment_info["linked_esaf_users"] = self._add_experiment_users_from_esaf(
                experiment_name=experiment_name,
                station_name=self._get_station_name(station_name),
                experimenters=esaf_experimenters,
            )

        return experiment_info

    def start_daq(
        self,
        experiment_name: str,
        data_directory: str,
        **daq_info: Any,
    ) -> dict[str, Any]:
        """Start real-time DM monitoring and upload for a data directory."""
        from apstools.utils import dm_api_daq

        daq_api = self._call_preserving_root_logging(dm_api_daq)
        daq = self._call_preserving_root_logging(
            daq_api.startDaq,
            experiment_name,
            data_directory,
            daq_info,
        )
        return _to_dict(daq)

    def stop_daq(self, experiment_name: str, data_directory: str) -> dict[str, Any]:
        """Stop real-time DM monitoring and upload for a data directory."""
        from apstools.utils import dm_api_daq

        daq_api = self._call_preserving_root_logging(dm_api_daq)
        daq = self._call_preserving_root_logging(
            daq_api.stopDaq,
            experiment_name,
            data_directory,
        )
        return _to_dict(daq)

    def upload(
        self,
        experiment_name: str,
        data_directory: str,
        **daq_info: Any,
    ) -> dict[str, Any]:
        """Submit a one-shot DM upload for files currently in a data directory."""
        from apstools.utils import dm_api_daq

        daq_api = self._call_preserving_root_logging(dm_api_daq)
        upload = self._call_preserving_root_logging(
            daq_api.upload,
            experiment_name,
            data_directory,
            daq_info,
        )
        return _to_dict(upload)


def get_dm_agent() -> DMAgent:
    """Return the session-wide DM agent, creating it on first use."""
    global _DM_AGENT
    if _DM_AGENT is None:
        _DM_AGENT = DMAgent()
    return _DM_AGENT

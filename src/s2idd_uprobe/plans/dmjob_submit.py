from dm.proc_web_service.api.workflowProcApi import WorkflowProcApi
from dm.common.utility.configurationManager import ConfigurationManager
from typing import Any
import logging

logger = logging.getLogger(__name__)

class DMAgent:
    def __init__(self):
        self.config_manager = ConfigurationManager.getInstance()
        self.dm_user, password = self.config_manager.parseLoginFile()
        proc_service_url = self.config_manager.getProcWebServiceUrl()
        self.workflow_api = WorkflowProcApi(self.dm_user, password, proc_service_url)

    def start_processing_job(
        self, workflow_name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Start a processing job for a workflow with given args."""
        job = {}
        try:
            job_obj = self.workflow_api.startProcessingJob(
                self.dm_user, workflow_name, args
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
            job_obj = self.workflow_api.getProcessingJobById(
                owner=self.dm_user, id=job_id
            )
            job = job_obj.getDictRep(keyList="ALL")
        except DmException as e:
            logger.error(f"ERROR: Unable to fetch processing job {job_id}")
            logger.error(e)
        return job


import yaml

xrf_workflow_path = '/home/beams/USER2IDD/bluesky-mic/src/s2idd_uprobe/configs/xrf_workflow.yml'

with open(xrf_workflow_path, "r") as f:
    workflow_config = yaml.safe_load(f)

print(workflow_config)
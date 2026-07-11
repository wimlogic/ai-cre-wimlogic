"""
AI-CRE WIMLOGIC V1 -- Phase 1A-BE WACP Client SDK Integration

services/ai_orchestration_service.py

Coordinator ONLY. This service no longer builds payloads, makes HTTP calls,
or maps result JSON onto AI-CRE tables itself - all of that now lives in:

    payload_builder.py   - builds the WACP data block (pure serializer)
    wacp_adapter.py       - the ONLY module that talks to the WACP Client SDK
    result_sync.py        - the single shared result-synchronization implementation

This module's only job is to coordinate those three in the right order and
manage the local WorkflowExecution lifecycle (create/update/event-log),
which is existing business logic that stays here since it doesn't belong
in a pure serializer, a pure protocol adapter, or the result-mapping module.

Public methods and their signatures are unchanged from before this
refactor - api/ai_orchestration.py (and therefore the existing frontend
API contract) requires no changes.
"""

import logging
import uuid
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings

# Coordinated services (Phase 1A-BE)
from app.services import payload_builder
from app.services import wacp_adapter
from app.services import result_sync

# Existing services (unchanged)
from app.services.workflow_execution_service import workflow_execution_service

# Existing CRUDs (unchanged)
from app.crud.api_usage_log import api_usage_log as crud_api_usage_log
from app.crud.project import project as crud_project

# Existing schemas (unchanged)
from app.schemas.workflow_execution import WorkflowExecutionCreate, WorkflowExecutionUpdate
from app.schemas.api_usage_log import ApiUsageLogCreate

# Existing models (unchanged)
from app.models.workflow_execution import WorkflowExecution

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# WACP job status (10_WACP_PROTOCOL.md §12.1) -> AI-CRE local execution
# status vocabulary.
#
# wacp_adapter deliberately returns the raw WACP status string untranslated
# (see wacp_adapter._normalize()) - mapping it onto AI-CRE's own local,
# pre-existing Title Case vocabulary (Pending/Running/Completed/Failed/
# Cancelled) is a business decision, so it lives here, alongside this
# service's other local status semantics, not inside the transport adapter.
#
# WACP's pre-queue states (RECEIVED/VALIDATING/ACCEPTED) have no distinct
# local equivalent - AI-CRE's execution record already starts "Pending" the
# moment it is created locally, before DEV-TOOLS is even contacted, so all
# three collapse onto "Pending". REJECTED (submission-time rejection, never
# even queued) maps onto "Failed", AI-CRE's existing terminal-failure state.
# ---------------------------------------------------------------------------

_WACP_STATUS_TO_LOCAL: Dict[str, str] = {
    "RECEIVED": "Pending",
    "VALIDATING": "Pending",
    "REJECTED": "Failed",
    "ACCEPTED": "Pending",
    "QUEUED": "Queued",
    "RUNNING": "Running",
    "COMPLETED": "Completed",
    "FAILED": "Failed",
    "CANCELLED": "Cancelled",
}

# AI-CRE's local terminal statuses. Cancelled is included alongside the
# pre-existing Completed/Failed pair now that WACP's job lifecycle (§12)
# actively uses CANCELLED - the pre-WACP implementation only ever checked
# ("Completed", "Failed") since the legacy protocol had no cancel concept.
_TERMINAL_LOCAL_STATUSES = ("Completed", "Failed", "Cancelled")


def _map_remote_status(raw_wacp_status: Optional[str]) -> Optional[str]:
    """
    Maps a raw WACP job status string (e.g. "RUNNING") onto AI-CRE's local
    execution status vocabulary (e.g. "Running").

    Returns None if `raw_wacp_status` is falsy, leaving the fallback choice
    to the caller. Falls back to a title-cased copy of any status this
    mapping doesn't recognize, rather than raising - a future WACP status
    value this SDK release doesn't yet know about should degrade to a
    reasonable display value, not break polling.
    """
    if not raw_wacp_status:
        return None
    key = raw_wacp_status.strip().upper()
    return _WACP_STATUS_TO_LOCAL.get(key, raw_wacp_status.strip().title())


# ---------------------------------------------------------------------------
# AI-CRE business pipeline code -> WACP workflow_code
#
# These are two separate namespaces. workflow_code as used throughout
# AI-CRE's own UI, execution history table, and local WorkflowExecution
# records (e.g. "ZONING_ANALYSIS") is AI-CRE's own business pipeline
# identifier - it predates WACP entirely and is independent of whatever
# workflow_code DEV-TOOLS assigns when a workflow is registered in its own
# catalog (e.g. "WF_PROPERTY_ANALYSIS"). Only the WACP-facing submission
# (wacp_adapter.submit_payload's workflow_code argument) needs the mapped
# value - the local execution record keeps AI-CRE's own pipeline code
# unchanged, exactly as before, so existing UI/history/business logic that
# reads WorkflowExecution.workflow_code is unaffected.
#
# Only pipelines DEV-TOOLS has actually registered and granted AICRE an
# active client_application_workflows binding for appear here. Submitting
# an unmapped pipeline fails clearly and locally (see
# _map_to_wacp_workflow_code below) rather than guessing at a WACP
# workflow_code that would just fail on DEV-TOOLS' side anyway.
_LOCAL_PIPELINE_TO_WACP_WORKFLOW_CODE: Dict[str, str] = {
    "ZONING_ANALYSIS": "WF_PROPERTY_ANALYSIS",
}


def _map_to_wacp_workflow_code(local_workflow_code: str) -> str:
    """Maps an AI-CRE business pipeline code to the WACP workflow_code
    registered with DEV-TOOLS for it.

    Raises ValueError (caught by the router's existing
    `except ValueError` -> HTTP 400 handling, same as an unknown
    project/property id) for any pipeline DEV-TOOLS has not yet been
    configured to accept. This intentionally fails before any WACP call is
    attempted and before the local execution record is even created -
    there is no reason to submit, or persist a Pending row for, a pipeline
    already known to have no corresponding DEV-TOOLS workflow.
    """
    mapped = _LOCAL_PIPELINE_TO_WACP_WORKFLOW_CODE.get(local_workflow_code)
    if not mapped:
        raise ValueError(
            f"Pipeline '{local_workflow_code}' has no WACP workflow_code mapping configured yet."
        )
    return mapped


class AIOrchestrationService:
    def submit_workflow(
        self,
        db: Session,
        *,
        project_id: int,
        property_id: int,
        workflow_code: str,
        scenario_id: Optional[int] = None,
        priority: str = "Normal",
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> WorkflowExecution:
        """
        Coordinates submission of a new AI request via WACP:

            Validate (via payload_builder) -> Build data block -> Submit
            through the WACP adapter -> Store execution -> Return response.

        Unchanged public signature - the existing frontend call
        (POST /ai-orchestration/submit) requires no changes.
        """
        # 1. Resolve the Project so its business project code (e.g.
        # "PRJ001") is available for the WACP envelope's `project_code`
        # field (10_WACP_PROTOCOL.md §7.2 requires the business code, never
        # a database primary key). payload_builder also validates the
        # project/property exist as part of building the data block below;
        # this lookup is a separate, lightweight read solely to obtain the
        # business code, not a duplicate validation pass.
        project_obj = crud_project.get(db, project_id)
        if not project_obj:
            raise ValueError(f"Project with ID '{project_id}' does not exist")

        # 1b. Resolve AI-CRE's business pipeline code to the WACP
        # workflow_code DEV-TOOLS actually expects. Resolved early,
        # deliberately before any execution record is created - see
        # _map_to_wacp_workflow_code's docstring.
        wacp_workflow_code = _map_to_wacp_workflow_code(workflow_code)

        # 2. Build the WACP envelope's `data` block. This also validates
        # that the referenced property exists (payload_builder.PayloadBuilderError
        # is a ValueError subclass, so the router's existing
        # `except ValueError` -> HTTP 400 handling covers it unchanged).
        data = payload_builder.build_enterprise_payload(
            db,
            project_id=project_id,
            property_id=property_id,
            metadata_json=metadata_json,
        )

        # 3. Create the local execution record in a "Pending" state before
        # attempting to contact the WACP server, so a request is always
        # tracked locally even if the outbound call fails.
        # devtools_execution_id starts null - AI-CRE never generates its
        # own ID for a remote job; it is set below only once the WACP
        # server returns the real one.
        execution_number = f"EXE-WIM-{uuid.uuid4().hex[:12].upper()}"

        execution_in = WorkflowExecutionCreate(
            execution_number=execution_number,
            project_id=project_id,
            property_id=property_id,
            scenario_id=scenario_id,
            workflow_code=workflow_code,
            workflow_version="1.0.0",
            devtools_execution_id=None,
            status="Pending",
            priority=priority,
            metadata_json=metadata_json or {},
        )
        execution_obj = workflow_execution_service.create_execution(db, execution_in=execution_in)

        workflow_execution_service.add_event(
            db,
            execution_id=execution_obj.execution_id,
            event_type="SYSTEM",
            status="Pending",
            message=f"Created workflow execution state {execution_number}. Dispatching via WACP.",
        )

        # 4. Submit through the WACP adapter. `execution_number` doubles as
        # the WACP `correlation_id` - it is already a unique, human-readable
        # identifier AI-CRE generates for every execution, so it needs no
        # separate generation step and lets an operator trace one execution
        # across both AI-CRE's own logs and the WACP server's.
        try:
            response = wacp_adapter.submit_payload(
                data,
                workflow_code=wacp_workflow_code,
                project_code=project_obj.project_id,
                priority=priority,
                correlation_id=execution_number,
            )

            # Existing API usage tracking, unchanged business behavior -
            # now reflects a real outbound WACP call instead of a
            # simulated one.
            api_log_in = ApiUsageLogCreate(
                provider="DEVTOOLS",
                api_name="SubmitPayload",
                endpoint="/wacp/v1/jobs",
                request_count=1,
                estimated_cost=0.0150,
            )
            crud_api_usage_log.create(db, obj_in=api_log_in)

            # Store the real WACP job ID from the normalized adapter
            # response - see wacp_adapter._normalize().
            remote_job_id = response.get("job_id")
            if remote_job_id:
                update_in = WorkflowExecutionUpdate(devtools_execution_id=str(remote_job_id))
                workflow_execution_service.update_execution(
                    db, execution_id=execution_obj.execution_id, execution_in=update_in
                )
            else:
                logger.warning(
                    "WACP submit response did not include a job_id for execution_id=%s",
                    execution_obj.execution_id,
                )

            workflow_execution_service.add_event(
                db,
                execution_id=execution_obj.execution_id,
                event_type="DISPATCH",
                status="Submitted",
                message=f"Successfully dispatched workflow request via WACP with Job ID: {remote_job_id or 'unknown'}.",
            )

        except wacp_adapter.DevToolsClientError as e:
            workflow_execution_service.add_event(
                db,
                execution_id=execution_obj.execution_id,
                event_type="ERROR",
                status="Failed",
                message=f"Failed to submit workflow via WACP: {str(e)}",
            )
            raise

        db.refresh(execution_obj)
        return execution_obj

    def check_workflow_status(self, db: Session, *, execution_id: int) -> str:
        """
        Coordinates a status check.

        If settings.ENABLE_WACP_POLLING is False, behaves exactly like the
        pre-Phase-4 implementation: local status only, no outbound call.

        If True, actively polls the WACP server via the adapter, and if the
        remote job has reached a terminal state, fetches its results and
        synchronizes them via the single shared result_sync implementation
        - the same one the webhook callback below uses.

        Unchanged public signature - the existing frontend call
        (GET /ai-orchestration/status/{execution_id}) requires no changes.
        """
        execution_obj = workflow_execution_service.get_execution(db, execution_id)
        if not execution_obj:
            raise ValueError(f"Workflow execution with ID '{execution_id}' not found")

        if execution_obj.status in _TERMINAL_LOCAL_STATUSES:
            return execution_obj.status

        if not settings.ENABLE_WACP_POLLING:
            # Exact pre-Phase-4 behavior: log a poll event, no outbound call.
            api_log_in = ApiUsageLogCreate(
                provider="DEVTOOLS",
                api_name="CheckWorkflowStatus",
                endpoint=f"/wacp/v1/jobs/{execution_obj.devtools_execution_id}/status",
                request_count=1,
                estimated_cost=0.0020,
            )
            crud_api_usage_log.create(db, obj_in=api_log_in)

            workflow_execution_service.add_event(
                db,
                execution_id=execution_obj.execution_id,
                event_type="POLL",
                status=execution_obj.status,
                message="Polled external status. No status change (polling disabled).",
            )
            return execution_obj.status

        if not execution_obj.devtools_execution_id:
            logger.warning(
                "Cannot poll WACP server for execution_id=%s: no devtools_execution_id stored yet.",
                execution_id,
            )
            return execution_obj.status

        api_log_in = ApiUsageLogCreate(
            provider="DEVTOOLS",
            api_name="GetJobStatus",
            endpoint=f"/wacp/v1/jobs/{execution_obj.devtools_execution_id}/status",
            request_count=1,
            estimated_cost=0.0020,
        )
        crud_api_usage_log.create(db, obj_in=api_log_in)

        try:
            status_response = wacp_adapter.get_job_status(execution_obj.devtools_execution_id)
        except wacp_adapter.DevToolsClientError as e:
            logger.warning(
                "Polling WACP status failed for execution_id=%s: %s", execution_id, e
            )
            workflow_execution_service.add_event(
                db,
                execution_id=execution_obj.execution_id,
                event_type="POLL",
                status=execution_obj.status,
                message=f"Failed to poll WACP status: {str(e)}",
            )
            return execution_obj.status

        raw_remote_status = status_response.get("status")
        local_status = _map_remote_status(raw_remote_status) or execution_obj.status

        if local_status not in _TERMINAL_LOCAL_STATUSES:
            workflow_execution_service.add_event(
                db,
                execution_id=execution_obj.execution_id,
                event_type="POLL",
                status=local_status,
                message=f"Polled WACP status: '{raw_remote_status}' (mapped to '{local_status}'). No terminal state yet.",
            )
            return local_status

        # Terminal state reached - fetch full results and synchronize via
        # the same shared result_sync implementation the webhook uses.
        # The actual results payload lives under `raw_response`, since
        # wacp_adapter wraps every response in the normalized
        # {job_id, status, raw_response} shape. `local_status` (not the raw
        # WACP status) is passed through, since result_sync's own field
        # mapping was built against AI-CRE's local status vocabulary.
        results_response = wacp_adapter.get_job_results(execution_obj.devtools_execution_id)
        synced_execution = result_sync.sync_job_result(
            db, execution=execution_obj, status=local_status, payload=results_response["raw_response"]
        )
        return synced_execution.status

    def receive_workflow_callback(
        self,
        db: Session,
        *,
        devtools_execution_id: str,
        status: str,
        payload: Dict[str, Any],
    ) -> WorkflowExecution:
        """
        Coordinates a webhook callback from DEV-TOOLS: look up the matching
        execution, then delegate entirely to the shared result_sync
        implementation - the same one future polling (check_workflow_status
        above) uses.

        Unchanged public signature - the existing frontend/webhook contract
        (POST /ai-orchestration/callback) requires no changes.
        """
        statement = select(WorkflowExecution).where(
            WorkflowExecution.devtools_execution_id == devtools_execution_id
        )
        execution_obj = db.execute(statement).scalars().first()
        if not execution_obj:
            raise ValueError(f"No workflow execution matches external DevTools ID '{devtools_execution_id}'")

        workflow_execution_service.add_event(
            db,
            execution_id=execution_obj.execution_id,
            event_type="CALLBACK",
            status=status,
            message=f"Received status update callback from DEV-TOOLS with status '{status}'.",
        )

        return result_sync.sync_job_result(db, execution=execution_obj, status=status, payload=payload)


ai_orchestration_service = AIOrchestrationService()

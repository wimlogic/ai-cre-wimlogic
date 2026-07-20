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
# AI-CRE business pipeline code -> DEV-TOOLS business_intent (WACP v1.1)
#
# These are two separate namespaces. workflow_code as used throughout
# AI-CRE's own UI, execution history table, and local WorkflowExecution
# records (e.g. "ZONING_ANALYSIS") is AI-CRE's own business pipeline
# identifier - it predates WACP entirely and has never been the same
# thing as any DEV-TOOLS-side identifier. Historically this table mapped
# a pipeline code to a specific WACP workflow_code (a legacy, now-stale
# routing mechanism); WACP v1.1 / DEV-TOOLS Build Week WIM Module V1
# introduced `business_intent` as the canonical routing field instead -
# a stable string WIM Module V1 matches against whichever workflow_code
# is actually registered and assigned to this Client Application, so
# AI-CRE never needs to know or send that internal DEV-TOOLS code at all.
# The local execution record keeps AI-CRE's own pipeline code unchanged,
# exactly as before, so existing UI/history/business logic that reads
# WorkflowExecution.workflow_code is unaffected.
#
# Only pipelines DEV-TOOLS has actually registered and granted AICRE an
# active client_application_workflows binding for appear here. Submitting
# an unmapped pipeline fails clearly and locally (see
# _map_to_business_intent below) rather than sending an unregistered
# business_intent that would just fail on DEV-TOOLS' side anyway.
_LOCAL_PIPELINE_TO_BUSINESS_INTENT: Dict[str, str] = {
    "ZONING_ANALYSIS": "PROPERTY_ANALYSIS",
}


def _map_to_business_intent(local_workflow_code: str) -> str:
    """Maps an AI-CRE business pipeline code to the business_intent value
    registered with DEV-TOOLS for it.

    Raises ValueError (caught by the router's existing
    `except ValueError` -> HTTP 400 handling, same as an unknown
    project/property id) for any pipeline DEV-TOOLS has not yet been
    configured to accept. This intentionally fails before any WACP call is
    attempted and before the local execution record is even created -
    there is no reason to submit, or persist a Pending row for, a pipeline
    already known to have no corresponding DEV-TOOLS business intent
    assignment.
    """
    mapped = _LOCAL_PIPELINE_TO_BUSINESS_INTENT.get(local_workflow_code)
    if not mapped:
        raise ValueError(
            f"Pipeline '{local_workflow_code}' has no business_intent mapping configured yet."
        )
    return mapped


class AIOrchestrationService:
    def create_pending_execution(
        self,
        db: Session,
        *,
        project_obj,
        property_id: int,
        scenario_id: Optional[int],
        local_workflow_code: str,
        priority: str,
        metadata_json: Optional[Dict[str, Any]],
        commit: bool = True,
    ) -> WorkflowExecution:
        """
        Creates the local execution record in a "Pending" state, BEFORE any
        outbound WACP call - extracted verbatim from submit_workflow()'s
        own prior inline logic (Phase 1A-BE), so a request is always
        tracked locally even if the outbound call never happens or fails.
        submit_workflow() below calls this immediately followed by
        dispatch_via_wacp() with nothing in between, for zero behavior
        change to the existing legacy caller.

        commit=True (default, unchanged): existing legacy behavior -
        both the execution row and its "Pending" event commit immediately,
        exactly as before this change.
        commit=False: participates in a service-owned transaction - Design
        Studio's Phase 1 local attempt registration
        (design_job_execution_service.py, Checkpoint 8) calls this with
        commit=False so the execution row and its event join that
        service's own single Phase 1 commit, alongside the
        DesignJobExecution bookkeeping and Design Job status update - the
        Design Job row lock stays held across all of it, and the whole
        thing commits or rolls back as one unit.

        This is also the Phase 1 (local, no-WACP) half of the two-phase
        attempt design app.services.design_job_execution_service.py
        (Checkpoint 8) uses for Design Studio: that service calls this
        method directly (never build_enterprise_payload, never the
        internal-pipeline-code translation table below - Design Studio
        Tool.workflow_code is already the exact DEV-TOOLS-registered
        code), then does its OWN Design Job Execution bookkeeping in the
        SAME transaction, THEN calls dispatch_via_wacp() separately, only
        after that transaction has committed - deliberately never holding
        the Design Job row lock across the network call.
        """
        execution_number = f"EXE-WIM-{uuid.uuid4().hex[:12].upper()}"

        execution_in = WorkflowExecutionCreate(
            execution_number=execution_number,
            project_id=project_obj.id,
            property_id=property_id,
            scenario_id=scenario_id,
            workflow_code=local_workflow_code,
            workflow_version="1.0.0",
            devtools_execution_id=None,
            status="Pending",
            priority=priority,
            metadata_json=metadata_json or {},
        )
        execution_obj = workflow_execution_service.create_execution(db, execution_in=execution_in, commit=commit)

        workflow_execution_service.add_event(
            db,
            execution_id=execution_obj.execution_id,
            event_type="SYSTEM",
            status="Pending",
            message=f"Created workflow execution state {execution_number}. Dispatching via WACP.",
            commit=commit,
        )
        return execution_obj

    def dispatch_via_wacp(
        self,
        db: Session,
        *,
        execution_obj: WorkflowExecution,
        project_obj,
        data: Dict[str, Any],
        priority: str,
        business_intent: Optional[str] = None,
        wacp_workflow_code: Optional[str] = None,
    ) -> WorkflowExecution:
        """
        Submits an ALREADY-CREATED Pending execution through WACP -
        extracted verbatim from submit_workflow()'s own prior inline
        logic. `data` is the exact WACP envelope data block to send: for
        submit_workflow() below, that's payload_builder's assembled
        Enterprise Payload; for Design Studio (Checkpoint 8), that's the
        Design Job's own frozen submitted_payload_json, passed through
        completely unmodified - this method has no awareness of, and
        performs no reconstruction of, either payload shape; it only ever
        forwards `data` to the WACP adapter as-is.

        `business_intent` / `wacp_workflow_code` (WACP v1.1): at least one
        must be provided by the caller (the WACP SDK itself enforces
        this, raising WacpEnvelopeError before any network call if both
        are None). submit_workflow() below passes `business_intent` -
        the canonical, WACP v1.1 routing field. Design Studio's caller
        (design_job_execution_service.py) continues to pass
        `wacp_workflow_code=job.workflow_code` unchanged - this method
        makes no assumption about which pipeline uses which field, it
        only forwards whatever it's given.

        On wacp_adapter.DevToolsClientError, the existing local execution
        row is NOT deleted or rolled back - only a Failed event is logged
        (existing behavior) - and the exception re-raises to the caller.
        """
        try:
            response = wacp_adapter.submit_payload(
                data,
                business_intent=business_intent,
                workflow_code=wacp_workflow_code,
                project_code=project_obj.project_id,
                priority=priority,
                correlation_id=execution_obj.execution_number,
            )

            api_log_in = ApiUsageLogCreate(
                provider="DEVTOOLS",
                api_name="SubmitPayload",
                endpoint="/wacp/v1/jobs",
                request_count=1,
                estimated_cost=0.0150,
            )
            crud_api_usage_log.create(db, obj_in=api_log_in)

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

        Unchanged public signature AND unchanged behavior - the existing
        frontend call (POST /ai-orchestration/submit) requires no changes.
        The body below is the exact same sequence as before this
        refactor, just factored into create_pending_execution() and
        dispatch_via_wacp() above, called back-to-back with nothing in
        between - this exists so Checkpoint 8's Design Studio execution
        path can reuse those two pieces directly without duplicating
        this orchestration logic, not to change this method's behavior.
        """
        project_obj = crud_project.get(db, project_id)
        if not project_obj:
            raise ValueError(f"Project with ID '{project_id}' does not exist")

        business_intent = _map_to_business_intent(workflow_code)

        data = payload_builder.build_enterprise_payload(
            db,
            project_id=project_id,
            property_id=property_id,
            metadata_json=metadata_json,
        )

        execution_obj = self.create_pending_execution(
            db,
            project_obj=project_obj,
            property_id=property_id,
            scenario_id=scenario_id,
            local_workflow_code=workflow_code,
            priority=priority,
            metadata_json=metadata_json,
        )

        return self.dispatch_via_wacp(
            db,
            execution_obj=execution_obj,
            project_obj=project_obj,
            business_intent=business_intent,
            data=data,
            priority=priority,
        )

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
        #
        # Fetch/sync failures are isolated from the remote completion
        # fact: DEV-TOOLS has already completed this job regardless of
        # whether AI-CRE successfully retrieves or maps that output. On
        # failure, execution.status is deliberately left NON-terminal
        # (never forced to "Completed" or "Failed") and
        # result_sync_error records what went wrong - the NEXT poll of
        # this same execution_id naturally retries this exact fetch+sync
        # step (nothing here re-submits or re-runs the remote workflow).
        # A successful sync clears result_sync_error back to None.
        try:
            results_response = wacp_adapter.get_job_results(execution_obj.devtools_execution_id)
            synced_execution = result_sync.sync_job_result(
                db, execution=execution_obj, status=local_status, payload=results_response["raw_response"]
            )
        except Exception as exc:
            logger.error(
                "Result synchronization failed for execution_id=%s after remote completion "
                "(status=%s): %s", execution_id, local_status, exc,
            )
            workflow_execution_service.update_execution(
                db, execution_id=execution_obj.execution_id,
                execution_in=WorkflowExecutionUpdate(result_sync_error=str(exc)),
            )
            workflow_execution_service.add_event(
                db, execution_id=execution_obj.execution_id, event_type="SYSTEM", status=execution_obj.status,
                message=f"DEV-TOOLS reported '{local_status}' but result synchronization failed: {exc}",
            )
            db.refresh(execution_obj)
            return execution_obj.status

        if synced_execution.result_sync_error is not None:
            workflow_execution_service.update_execution(
                db, execution_id=synced_execution.execution_id,
                execution_in=WorkflowExecutionUpdate(result_sync_error=None),
            )
            db.refresh(synced_execution)
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

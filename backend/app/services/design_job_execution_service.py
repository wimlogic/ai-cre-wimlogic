"""
app/services/design_job_execution_service.py

AI HOME WIMLOGIC -- Design Studio -- V1.1D Design Job
Stage D (EXECUTE / RETRY) business service - Checkpoint 8.

Converts a frozen, submitted Design Job (Checkpoint 7's output) into one
or more runtime Workflow Execution attempts via the EXISTING, unmodified
AIOrchestrationService / WorkflowExecutionService / WACP adapter seam.

Locked distinction:
    Design Job            = persistent AI Home business intent
    Workflow Execution     = one runtime processing attempt
    Design Job Execution   = association/bookkeeping row between the two

Relationship: ONE Design Job -> MANY Workflow Execution attempts.

This service explicitly does NOT:
    - call payload_builder.build_enterprise_payload()
    - call payload_builder.build_design_job_context()
    - call payload_builder.build_design_job_inputs()
    - resolve Tool Option defaults
    - re-validate selected images
    - rebuild submitted_payload_json in any way

All of that happened once, at Checkpoint 7 freeze. The same immutable
frozen JSON business payload, semantically identical with no
business-field reconstruction or mutation, is the only business payload
ever passed to WACP here.

TWO-PHASE ATTEMPT DESIGN (corrected for atomicity)
---------------------------------------------------
Phase 1 (local, DB-only) is now genuinely ONE atomic transaction, held
under a SINGLE acquisition of the Design Job row lock, from the initial
lifecycle validation all the way through the final commit - there is no
longer any intermediate commit inside Phase 1. This closes the prior
orphan-state window where Design Job.status could reach 'processing' (or
a prior attempt's is_current could reach 0) before a complete new
attempt actually existed.

    lock Design Job FOR UPDATE
    -> validate lifecycle (status, frozen payload, retry eligibility)
    -> validate media URL configuration (no network fetch)
    -> resolve the AI-CRE Project surrogate (job.project_id VARCHAR ->
       cre_projects.id) - if this fails, ROLLBACK, no writes have
       happened yet
    -> create local Workflow Execution in Pending, commit=False
       (app.services.ai_orchestration_service.create_pending_execution)
    -> [retry only] flip the prior current attempt's is_current to 0,
       commit=False
    -> assign next attempt_number under the still-held lock
    -> create new DesignJobExecution is_current=1, commit=False
    -> [execute only] update Design Job status 'submitted' -> 'processing',
       commit=False
    -> COMMIT ONCE
    -> release Design Job lock

On ANY exception before that single commit: ROLLBACK. The prior state
(status='submitted' and no attempt, for execute; prior attempt still
is_current=1 and no new attempt, for retry) is fully preserved - never a
partial/orphan state.

Phase 2 (network, NO DB lock held) runs only after Phase 1's commit:
AIOrchestrationService.dispatch_via_wacp() submits the exact frozen
submitted_payload_json. On DevToolsClientError, the already-committed
Phase 1 rows are NOT deleted or rolled back - only the existing
Failed-event logging (inside dispatch_via_wacp itself) applies, and the
exception propagates to the caller.
"""
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.config import settings

from app.crud.design_job import design_job as crud_design_job
from app.crud.design_job_execution import design_job_execution as crud_design_job_execution
from app.crud.project import project as crud_project

from app.services.ai_orchestration_service import ai_orchestration_service
from app.services.workflow_execution_service import workflow_execution_service
from app.services import wacp_adapter

from app.models.design_job import DesignJob
from app.models.design_job_execution import DesignJobExecution


class DesignJobExecutionNotFoundError(ValueError):
    """Raised when the Design Job does not exist - maps to HTTP 404."""
    pass


class DesignJobExecutionValidationError(ValueError):
    """Raised for structural/caller-mistake eligibility failures (e.g. still draft, no frozen payload, project unresolvable) - maps to HTTP 400."""
    pass


class DesignJobExecutionConflictError(ValueError):
    """Raised when the Job/attempt is not currently eligible due to its OWN state (already processing, attempt still active) - maps to HTTP 409."""
    pass


_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}


def _is_loopback_host(host: Optional[str]) -> bool:
    if not host:
        return False
    return host.lower() in _LOOPBACK_HOSTS


class DesignJobExecutionService:

    # ------------------------------------------------------------------
    # Media URL configuration-awareness validation (no network fetch)
    # ------------------------------------------------------------------

    def _validate_media_url_compatibility(self, job: DesignJob) -> None:
        """
        Structural + configuration-awareness check only - never a
        speculative network fetch from the API request path. Does NOT
        mutate submitted_payload_json in any way; this only decides
        whether to allow or block the submission attempt.

        For every submitted_payload_json.inputs.images[*].url:
            1. Must parse as a structurally valid http/https URL with a host.
            2. If the configured settings.WACP_BASE_URL is a remote
               (non-loopback) host while this image URL is loopback-only,
               block with a clear configuration error - DEV-TOOLS running
               on a remote/deployed host could never fetch a
               127.0.0.1-only URL. If both are local/loopback (typical
               single-machine development), or if the image URL is
               itself already a remote absolute URL, allow it.
        """
        payload = job.submitted_payload_json or {}
        images = (payload.get("inputs") or {}).get("images", [])

        wacp_base = settings.WACP_BASE_URL
        wacp_parsed = urlparse(wacp_base) if wacp_base else None
        wacp_is_remote = bool(wacp_parsed and wacp_parsed.hostname and not _is_loopback_host(wacp_parsed.hostname))

        for entry in images:
            url = entry.get("url")
            parsed = urlparse(url or "")
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                raise DesignJobExecutionValidationError(
                    f"Selected image URL '{url}' is not a structurally valid http/https URL"
                )
            if wacp_is_remote and _is_loopback_host(parsed.hostname):
                raise DesignJobExecutionValidationError(
                    f"Selected image URL '{url}' is loopback/local-only, but the configured WACP_BASE_URL "
                    f"('{wacp_base}') is a remote host - DEV-TOOLS would not be able to fetch this image. "
                    f"APP_BASE_URL / media hosting must be externally reachable before this Design Job can "
                    f"be executed against a remote DEV-TOOLS environment."
                )

    # ------------------------------------------------------------------
    # Shared Phase 1 (single transaction) + Phase 2 (network) tail
    # ------------------------------------------------------------------

    def _register_attempt_and_dispatch(
        self, db: Session, *, job: DesignJob, project_obj, prior_attempt_to_clear: Optional[DesignJobExecution]
    ) -> DesignJobExecution:
        """
        Runs the ENTIRE local attempt registration as ONE transaction
        (Phase 1), committing exactly once, then dispatches via WACP
        (Phase 2) only after that commit succeeds.

        prior_attempt_to_clear: pass the CURRENT attempt row (already
        loaded by the caller, within the same lock/transaction) to flip
        its is_current to 0 as part of retry, in the SAME commit as the
        new attempt's creation. Pass None for the initial execute (no
        prior attempt exists yet) - in that case this method also
        transitions the Design Job status 'submitted' -> 'processing' in
        the same commit, since there is no prior-attempt flip to serve as
        the atomic marker instead.
        """
        try:
            execution_obj = ai_orchestration_service.create_pending_execution(
                db,
                project_obj=project_obj,
                property_id=job.property_id,
                scenario_id=None,
                local_workflow_code=job.workflow_code,
                priority="Normal",
                metadata_json=None,
                commit=False,
            )

            if prior_attempt_to_clear is not None:
                crud_design_job_execution.update(db, db_obj=prior_attempt_to_clear, obj_in={"is_current": 0}, commit=False)

            next_attempt = crud_design_job_execution.get_max_attempt_number(db, design_job_id=job.id) + 1
            new_attempt = crud_design_job_execution.create(
                db,
                obj_in={
                    "design_job_id": job.id,
                    "workflow_execution_id": execution_obj.execution_id,
                    "attempt_number": next_attempt,
                    "is_current": 1,
                },
                commit=False,
            )

            if prior_attempt_to_clear is None:
                # Initial execute: this status flip is the atomic marker
                # that a complete attempt now exists - it commits in the
                # SAME transaction as the attempt row itself, never before.
                crud_design_job.update(db, db_obj=job, obj_in={"status": "processing"}, commit=False)

            db.commit()
            db.refresh(new_attempt)
            db.refresh(execution_obj)
        except Exception:
            db.rollback()
            raise

        # Phase 2 - network call, no DB lock held, runs only after Phase 1
        # has fully committed. On DevToolsClientError, dispatch_via_wacp()
        # itself logs the Failed event and re-raises; the already-
        # committed rows above are left exactly as they are.
        ai_orchestration_service.dispatch_via_wacp(
            db,
            execution_obj=execution_obj,
            project_obj=project_obj,
            wacp_workflow_code=job.workflow_code,
            data=job.submitted_payload_json,
            priority="Normal",
        )

        return new_attempt

    # ------------------------------------------------------------------
    # EXECUTE - initial attempt
    # ------------------------------------------------------------------

    def execute_submitted_job(self, db: Session, *, job_id: int) -> DesignJobExecution:
        """
        Creates the FIRST Workflow Execution attempt for an already-
        submitted, frozen Design Job.

        Lock the Design Job row once, validate everything, resolve the
        Project, then hand off to _register_attempt_and_dispatch() which
        performs the entire local registration (Workflow Execution
        creation, DesignJobExecution insert, status 'submitted' ->
        'processing') as ONE commit. The row lock is held continuously
        from the first lock_for_update() call until that single commit -
        this IS the concurrency gate: a second concurrent /execute call
        blocks on the row lock for the full duration, then re-reads and
        finds status already 'processing' - correctly rejected (TEST H),
        never creating a second attempt, and never observing a
        half-registered state.
        """
        job = crud_design_job.lock_for_update(db, job_id)
        if not job:
            raise DesignJobExecutionNotFoundError(f"Design Job {job_id} not found")

        if job.status == "draft":
            db.rollback()
            raise DesignJobExecutionValidationError(
                f"Design Job {job_id} is still draft; it must be submitted before it can be executed"
            )
        if job.status != "submitted":
            db.rollback()
            raise DesignJobExecutionConflictError(
                f"Design Job {job_id} is not in 'submitted' status (status='{job.status}'); "
                f"it may already be executing or have been executed"
            )
        if not job.submitted_payload_json:
            db.rollback()
            raise DesignJobExecutionValidationError(
                f"Design Job {job_id} has no frozen submitted_payload_json; it cannot be executed"
            )

        self._validate_media_url_compatibility(job)

        project_obj = crud_project.get_by_project_id(db, job.project_id)
        if not project_obj:
            db.rollback()
            raise DesignJobExecutionValidationError(
                f"Project '{job.project_id}' not found - cannot resolve internal project reference for WACP submission"
            )

        return self._register_attempt_and_dispatch(db, job=job, project_obj=project_obj, prior_attempt_to_clear=None)

    # ------------------------------------------------------------------
    # RETRY - subsequent attempt, same frozen payload
    # ------------------------------------------------------------------

    def retry_design_job(self, db: Session, *, job_id: int) -> DesignJobExecution:
        """
        Creates a NEW Workflow Execution attempt for the SAME Design Job,
        reusing the exact same frozen submitted_payload_json - never
        rebuilt, never re-validated against Tool/Image/Option definitions.

        Retry eligibility (source-verified): the CURRENT attempt's
        associated cre_workflow_executions.status must be 'Failed'.
        This is reliably determinable today without depending on any
        not-yet-implemented Design-Studio-specific result ingestion:
            - An immediate WACP dispatch failure (DevToolsClientError)
              already sets the execution's status to 'Failed'
              synchronously, inside the existing dispatch_via_wacp().
            - A later, async DEV-TOOLS-side failure discovered via the
              EXISTING, generic, already-working
              check_workflow_status()/receive_workflow_callback() ->
              result_sync.sync_job_result() path also sets 'Failed' on
              the execution row - that path is generic (keyed off
              execution_id, not Design-Studio-aware) and works today
              regardless of whether Design Image Version persistence
              (a later checkpoint) exists yet.

        Lock the Design Job row once, validate everything (including
        loading and checking the CURRENT attempt's Workflow Execution
        status), resolve the Project, then hand off to
        _register_attempt_and_dispatch() with prior_attempt_to_clear set
        to the current attempt - the is_current flip and the new attempt's
        creation happen in the SAME commit. The row lock is held
        continuously from the first lock_for_update() call until that
        commit - a second concurrent /retry call blocks for the full
        duration, then re-reads get_current() and finds either the
        winner's new attempt (status not yet 'Failed', so not
        retry-eligible) or, if it re-reads at exactly the wrong instant,
        no attempt flagged current at all - either way it is cleanly
        rejected (TEST P), never creating a second next-attempt.
        """
        job = crud_design_job.lock_for_update(db, job_id)
        if not job:
            raise DesignJobExecutionNotFoundError(f"Design Job {job_id} not found")

        if not job.submitted_payload_json:
            db.rollback()
            raise DesignJobExecutionValidationError(
                f"Design Job {job_id} has no frozen submitted_payload_json; it cannot be retried"
            )

        current = crud_design_job_execution.get_current(db, design_job_id=job.id)
        if not current:
            db.rollback()
            raise DesignJobExecutionValidationError(
                f"Design Job {job_id} has no prior execution attempt; use /execute first"
            )

        current_workflow_execution = workflow_execution_service.get_execution(db, current.workflow_execution_id)
        if not current_workflow_execution:
            db.rollback()
            raise DesignJobExecutionValidationError(
                f"Design Job {job_id}'s current attempt references a Workflow Execution that no longer exists"
            )
        if current_workflow_execution.status != "Failed":
            db.rollback()
            raise DesignJobExecutionConflictError(
                f"Design Job {job_id}'s current attempt is not retry-eligible "
                f"(status='{current_workflow_execution.status}'); only a 'Failed' attempt may be retried"
            )

        self._validate_media_url_compatibility(job)

        project_obj = crud_project.get_by_project_id(db, job.project_id)
        if not project_obj:
            db.rollback()
            raise DesignJobExecutionValidationError(
                f"Project '{job.project_id}' not found - cannot resolve internal project reference for WACP submission"
            )

        return self._register_attempt_and_dispatch(db, job=job, project_obj=project_obj, prior_attempt_to_clear=current)

    # ------------------------------------------------------------------
    # Execution history (read-only)
    # ------------------------------------------------------------------

    def get_executions(self, db: Session, *, job_id: int) -> Optional[Tuple[List[DesignJobExecution], int]]:
        job = crud_design_job.get(db, job_id)
        if not job:
            return None
        return crud_design_job_execution.get_multi(db, design_job_id=job_id, limit=500)


design_job_execution_service = DesignJobExecutionService()

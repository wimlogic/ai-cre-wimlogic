"""
tests/services/test_completed_with_warnings.py

AIHOME WACP compatibility update: DEV-TOOLS WIM Module V2 introduced a
new terminal status, COMPLETED_WITH_WARNINGS, which the WACP client SDK's
closed JobStatus enum previously rejected outright (wacp.core.
serialization.dict_to_response raised WacpEnvelopeError("Invalid status
value: 'COMPLETED_WITH_WARNINGS'")), causing every poll of such a job to
fail silently, forever, with outputs never retrieved.

Verifies, at every layer in the chain, that all four statuses named in
the compatibility update behave correctly:
  COMPLETED               - retrieve outputs, sync, display "Completed"
  COMPLETED_WITH_WARNINGS - retrieve outputs, sync, display "Completed
                            with Warnings" (never treated as FAILED)
  FAILED                  - unaffected, still routes to the failure path
  CANCELLED               - unaffected, still routes to the failure path
                            (its pre-existing behavior, unchanged)
"""
import json

import pytest

from app.db.database import SessionLocal
from app.models.project import Project
from app.models.property import Property
from app.models.project_property import ProjectProperty
from app.models.workflow_execution import WorkflowExecution

from wacp.core.enums import JobStatus, is_terminal
from wacp.core.serialization import dict_to_response
from wacp.core.errors import WacpEnvelopeError

from app.services.ai_orchestration_service import _map_remote_status, _TERMINAL_LOCAL_STATUSES
from app.services.result_sync import sync_job_result


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _make_execution(db, suffix):
    proj = Project(project_id=f"PRJ-{suffix}", project_name="Status Compatibility Test")
    db.add(proj); db.commit()
    prop = Property(property_uid=f"PROP-{suffix}", address="1 Status Test St")
    db.add(prop); db.commit(); db.refresh(prop)
    db.add(ProjectProperty(project_id=f"PRJ-{suffix}", property_id=prop.id)); db.commit()
    execution = WorkflowExecution(
        execution_number=f"EXE-{suffix}", project_id=proj.id, property_id=prop.id,
        workflow_code="PROPERTY_INTELLIGENCE", status="Running", priority="Normal",
    )
    db.add(execution); db.commit(); db.refresh(execution)
    return execution


def _minimal_wacp_response_payload(status: str) -> dict:
    return {
        "wacp": {
            "version": "1.1", "request_id": "req-1", "response_id": "resp-1",
            "job_id": "job-1", "timestamp": "2026-07-24T00:00:00Z",
        },
        "status": status,
    }


def _completed_result_payload() -> dict:
    return {"outputs": [{"output_type": "json", "title": "Final Property Analysis", "content": json.dumps({
        "executive_summary": "Status compatibility test summary.",
        "key_findings": ["A"], "business_health": "Sound.",
        "priority_actions": ["B"], "recommendations": ["C"], "conclusion": "Proceed.",
    })}]}


class TestWacpSdkEnumLayer:
    """The root cause and its fix: wacp.core.enums.JobStatus and the
    serialization layer that previously rejected this value outright."""

    def test_completed_with_warnings_is_a_valid_enum_member(self):
        assert JobStatus("COMPLETED_WITH_WARNINGS") == JobStatus.COMPLETED_WITH_WARNINGS

    def test_completed_with_warnings_is_terminal(self):
        assert is_terminal(JobStatus.COMPLETED_WITH_WARNINGS) is True

    def test_completed_is_still_terminal(self):
        assert is_terminal(JobStatus.COMPLETED) is True

    def test_failed_is_still_terminal(self):
        assert is_terminal(JobStatus.FAILED) is True

    def test_cancelled_is_still_terminal(self):
        assert is_terminal(JobStatus.CANCELLED) is True

    def test_dict_to_response_no_longer_raises_for_completed_with_warnings(self):
        """This is the exact failure the compatibility update fixes -
        this call used to raise WacpEnvelopeError("Invalid status
        value: 'COMPLETED_WITH_WARNINGS'")."""
        payload = _minimal_wacp_response_payload("COMPLETED_WITH_WARNINGS")
        response = dict_to_response(payload)
        assert response.status == JobStatus.COMPLETED_WITH_WARNINGS

    def test_dict_to_response_still_rejects_genuinely_unknown_status(self):
        """The fix must not turn dict_to_response into a permissive
        parser - a truly unrecognized status must still raise, exactly
        as before."""
        payload = _minimal_wacp_response_payload("SOME_FUTURE_STATUS_NOT_YET_SUPPORTED")
        with pytest.raises(WacpEnvelopeError):
            dict_to_response(payload)

    def test_dict_to_response_still_parses_completed(self):
        response = dict_to_response(_minimal_wacp_response_payload("COMPLETED"))
        assert response.status == JobStatus.COMPLETED

    def test_dict_to_response_still_parses_failed(self):
        response = dict_to_response(_minimal_wacp_response_payload("FAILED"))
        assert response.status == JobStatus.FAILED

    def test_dict_to_response_still_parses_cancelled(self):
        response = dict_to_response(_minimal_wacp_response_payload("CANCELLED"))
        assert response.status == JobStatus.CANCELLED


class TestLocalStatusMapping:
    """ai_orchestration_service._map_remote_status and
    _TERMINAL_LOCAL_STATUSES - the layer that decides AI-CRE's own
    displayed status string."""

    def test_completed_with_warnings_maps_to_its_own_distinct_status(self):
        assert _map_remote_status("COMPLETED_WITH_WARNINGS") == "Completed with Warnings"

    def test_completed_with_warnings_is_a_local_terminal_status(self):
        assert "Completed with Warnings" in _TERMINAL_LOCAL_STATUSES

    def test_completed_still_maps_correctly(self):
        assert _map_remote_status("COMPLETED") == "Completed"

    def test_failed_still_maps_correctly(self):
        assert _map_remote_status("FAILED") == "Failed"

    def test_cancelled_still_maps_correctly(self):
        assert _map_remote_status("CANCELLED") == "Cancelled"

    def test_case_insensitivity_preserved_for_new_status(self):
        assert _map_remote_status("completed_with_warnings") == "Completed with Warnings"


class TestResultSyncRouting:
    """sync_job_result - the layer that decides whether a status routes
    to the success path (_sync_completed_job, retrieving and storing
    outputs) or the failure path (_sync_failed_job). This is where "Do
    NOT treat it as FAILED" is actually enforced."""

    def test_completed_routes_to_success_path_and_displays_completed(self, db):
        execution = _make_execution(db, "CWW-1")
        result = sync_job_result(db, execution=execution, status="Completed", payload=_completed_result_payload())
        assert result.status == "Completed"

    def test_completed_with_warnings_routes_to_success_path_not_failed(self, db):
        """The central assertion of this compatibility update: outputs
        ARE retrieved and synchronized (not silently dropped), and the
        execution ends up displaying "Completed with Warnings" - never
        "Failed"."""
        execution = _make_execution(db, "CWW-2")
        result = sync_job_result(
            db, execution=execution, status="Completed with Warnings", payload=_completed_result_payload()
        )
        assert result.status == "Completed with Warnings"
        assert result.status != "Failed"

    def test_completed_with_warnings_actually_persists_the_business_report(self, db):
        """Not just a status string change - the outputs must genuinely
        be retrieved and synced, exactly as for a plain COMPLETED job."""
        from app.models.property_analysis_report import PropertyAnalysisReport
        execution = _make_execution(db, "CWW-3")
        sync_job_result(db, execution=execution, status="Completed with Warnings", payload=_completed_result_payload())
        report = db.query(PropertyAnalysisReport).filter(
            PropertyAnalysisReport.workflow_execution_id == execution.execution_id
        ).first()
        assert report is not None
        assert report.report_json["executive_summary"] == "Status compatibility test summary."

    def test_completed_with_warnings_raw_uppercase_from_webhook_also_works(self, db):
        """The webhook callback path passes DEV-TOOLS' raw string
        verbatim, unmapped - confirms case-insensitive matching handles
        this caller too, not just the polling path's pre-mapped Title
        Case string."""
        execution = _make_execution(db, "CWW-4")
        result = sync_job_result(
            db, execution=execution, status="COMPLETED_WITH_WARNINGS", payload=_completed_result_payload()
        )
        assert result.status == "Completed with Warnings"

    def test_failed_still_routes_to_failure_path_unaffected(self, db):
        execution = _make_execution(db, "CWW-5")
        result = sync_job_result(
            db, execution=execution, status="Failed",
            payload={"error_message": "Simulated remote failure."},
        )
        assert result.status == "Failed"

    def test_cancelled_still_routes_to_failure_path_unaffected(self, db):
        """Pre-existing, documented behavior (CANCELLED has no dedicated
        success/failure distinction of its own in sync_job_result - it
        has always routed through the failure path). This compatibility
        update must not change that."""
        execution = _make_execution(db, "CWW-6")
        result = sync_job_result(
            db, execution=execution, status="Cancelled",
            payload={"error_message": "Job was cancelled."},
        )
        assert result.status == "Failed"  # unchanged pre-existing behavior

    def test_idempotency_guard_recognizes_completed_with_warnings(self, db):
        """An execution already finalized as "Completed with Warnings"
        must be returned unchanged on a second call, exactly like the
        pre-existing Completed/Failed guard."""
        execution = _make_execution(db, "CWW-7")
        sync_job_result(db, execution=execution, status="Completed with Warnings", payload=_completed_result_payload())
        db.refresh(execution)
        assert execution.status == "Completed with Warnings"

        # Second call - must be a no-op (idempotency guard short-circuits
        # before touching anything).
        result2 = sync_job_result(db, execution=execution, status="Completed with Warnings", payload=_completed_result_payload())
        assert result2.status == "Completed with Warnings"

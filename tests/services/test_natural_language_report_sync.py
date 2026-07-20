"""
tests/services/test_natural_language_report_sync.py

Render Completed DEV-TOOLS Output as Natural-Language Report - backend
test coverage: deterministic output selection, natural-language report
section mapping, backward compatibility, malformed-output fallback, and
result-sync failure isolation/retry.
"""
import datetime
import json
from unittest.mock import patch

import pytest

from app.db.database import SessionLocal
from app.models.project import Project
from app.models.property import Property

from app.services.result_sync import (
    _select_final_output,
    _build_natural_language_report_sections,
    ResultSyncError,
    sync_job_result,
)
from app.services import wacp_adapter, result_sync
from app.services.ai_orchestration_service import ai_orchestration_service
from app.services.workflow_execution_service import workflow_execution_service
from app.schemas.workflow_execution import WorkflowExecutionCreate


# ---------------------------------------------------------------------------
# _select_final_output - deterministic selection, no insertion-order reliance
# ---------------------------------------------------------------------------

class TestSelectFinalOutput:
    def test_direct_shape_returns_result_data_itself(self):
        result_data = {"executive_summary": "Summary text.", "conclusion": "Final word."}
        assert _select_final_output(result_data) is result_data

    def test_legacy_property_analysis_shape_returns_result_data_itself(self):
        result_data = {"property_analysis": {"estimate_low": 1000}}
        assert _select_final_output(result_data) is result_data

    def test_nested_outputs_dict_selected_by_is_final_flag_not_last_key(self):
        result_data = {
            "outputs": {
                "step_a": {"is_final": False, "executive_summary": "Wrong - not final."},
                "step_b": {"is_final": True, "executive_summary": "Correct - flagged final."},
                # "step_b" is NOT the last key here on purpose - proves
                # selection isn't based on dict/insertion order.
                "step_c_not_final": {"is_final": False, "executive_summary": "Also wrong."},
            }
        }
        selected = _select_final_output(result_data)
        assert selected["executive_summary"] == "Correct - flagged final."

    def test_nested_steps_list_selected_by_highest_sequence_not_array_position(self):
        result_data = {
            "steps": [
                {"sequence": 3, "executive_summary": "Highest sequence - correct."},
                {"sequence": 1, "executive_summary": "Lowest sequence."},
                {"sequence": 2, "executive_summary": "Middle sequence."},
            ]
        }
        # The correct entry (sequence=3) is deliberately FIRST in the list,
        # not last - proves selection isn't based on array position.
        selected = _select_final_output(result_data)
        assert selected["executive_summary"] == "Highest sequence - correct."

    def test_nested_collection_with_no_explicit_marker_raises(self):
        result_data = {"outputs": {"a": {"executive_summary": "x"}, "b": {"executive_summary": "y"}}}
        with pytest.raises(ResultSyncError, match="cannot determine the final output deterministically"):
            _select_final_output(result_data)

    def test_unrecognized_shape_returns_input_unchanged(self):
        result_data = {"something_else_entirely": True}
        assert _select_final_output(result_data) == result_data


# ---------------------------------------------------------------------------
# _build_natural_language_report_sections
# ---------------------------------------------------------------------------

class TestBuildSections:
    def test_all_six_fields_present(self):
        output = {
            "executive_summary": "Summary.",
            "key_findings": ["Finding 1", "Finding 2"],
            "business_health": "Healthy overall.",
            "priority_actions": ["Action 1"],
            "recommendations": ["Recommend X", "Recommend Y"],
            "conclusion": "Overall positive.",
        }
        sections = _build_natural_language_report_sections(output)
        assert len(sections) == 6
        assert [s["section_type"] for s in sections] == [
            "executive_summary", "key_findings", "business_health",
            "priority_actions", "recommendations", "conclusion",
        ]

    def test_list_fields_json_encoded(self):
        output = {"key_findings": ["A", "B", "C"]}
        sections = _build_natural_language_report_sections(output)
        assert json.loads(sections[0]["content"]) == ["A", "B", "C"]

    def test_paragraph_fields_stored_as_plain_text(self):
        output = {"executive_summary": "Plain prose text."}
        sections = _build_natural_language_report_sections(output)
        assert sections[0]["content"] == "Plain prose text."

    def test_missing_field_produces_no_section(self):
        output = {"executive_summary": "Only this one."}
        sections = _build_natural_language_report_sections(output)
        assert len(sections) == 1
        assert sections[0]["section_type"] == "executive_summary"

    def test_display_order_is_fixed_reading_order_not_input_order(self):
        # Deliberately out-of-order input dict.
        output = {"conclusion": "c", "executive_summary": "a", "key_findings": ["b"]}
        sections = _build_natural_language_report_sections(output)
        orders = {s["section_type"]: s["display_order"] for s in sections}
        assert orders["executive_summary"] < orders["key_findings"] < orders["conclusion"]

    def test_list_field_arriving_as_single_string_normalized_to_list(self):
        output = {"key_findings": "Single finding, not a list."}
        sections = _build_natural_language_report_sections(output)
        assert json.loads(sections[0]["content"]) == ["Single finding, not a list."]

    def test_empty_output_produces_no_sections(self):
        assert _build_natural_language_report_sections({}) == []


# ---------------------------------------------------------------------------
# Integration: sync_job_result end-to-end, real DB
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def execution(db):
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    proj = Project(project_id=f"PRJ-{suffix}", project_name="NL Report Test Project")
    db.add(proj)
    db.commit()
    db.refresh(proj)

    prop = Property(property_uid=f"PROP-{suffix}", address="1 Report St")
    db.add(prop)
    db.commit()
    db.refresh(prop)

    exec_obj = workflow_execution_service.create_execution(db, execution_in=WorkflowExecutionCreate(
        execution_number=f"EXE-{suffix}", project_id=proj.id, property_id=prop.id, scenario_id=None,
        workflow_code="ZONING_ANALYSIS", workflow_version="1.0.0", devtools_execution_id=f"JOB-{suffix}",
        status="Running", priority="Normal", metadata_json={},
    ))
    return exec_obj


class TestSyncJobResultIntegration:
    def test_completed_new_shape_persists_raw_and_sections(self, db, execution):
        payload = {
            "version": "2.0.0",
            "results": {
                "executive_summary": "The property shows strong development potential.",
                "key_findings": ["Zoning allows mixed use.", "Lot size exceeds minimum."],
                "business_health": "Financially sound with moderate risk.",
                "priority_actions": ["File SB-9 application.", "Commission survey."],
                "recommendations": ["Proceed with duplex conversion."],
                "conclusion": "Recommended to proceed.",
            },
        }
        synced = sync_job_result(db, execution=execution, status="Completed", payload=payload)

        assert synced.status == "Completed"
        assert synced.result_sync_error is None

        from app.models.property_analysis_report import PropertyAnalysisReport
        report = db.query(PropertyAnalysisReport).filter(
            PropertyAnalysisReport.workflow_execution_id == execution.execution_id
        ).first()
        assert report is not None
        assert report.report_json["executive_summary"] == "The property shows strong development potential."
        assert report.recommendation == "Recommended to proceed."  # mapped from conclusion

        from app.models.result_section import ResultSection
        from app.models.workflow_result import WorkflowResult
        result_row = db.query(WorkflowResult).filter(WorkflowResult.execution_id == execution.execution_id).first()
        sections = db.query(ResultSection).filter(ResultSection.result_id == result_row.result_id).order_by(ResultSection.display_order).all()
        section_types = [s.section_type for s in sections]
        assert "executive_summary" in section_types
        assert "key_findings" in section_types
        assert json.loads([s for s in sections if s.section_type == "key_findings"][0].content) == [
            "Zoning allows mixed use.", "Lot size exceeds minimum.",
        ]

    def test_missing_optional_section_not_persisted(self, db, execution):
        payload = {"version": "2.0.0", "results": {"executive_summary": "Only a summary, nothing else."}}
        sync_job_result(db, execution=execution, status="Completed", payload=payload)

        from app.models.result_section import ResultSection
        from app.models.workflow_result import WorkflowResult
        result_row = db.query(WorkflowResult).filter(WorkflowResult.execution_id == execution.execution_id).first()
        sections = db.query(ResultSection).filter(ResultSection.result_id == result_row.result_id).all()
        section_types = {s.section_type for s in sections}
        assert section_types == {"executive_summary"}

    def test_legacy_shape_still_works_unchanged(self, db, execution):
        payload = {
            "version": "1.0.0",
            "results": {"property_analysis": {"estimate_low": 25000, "estimate_high": 42000, "recommendation": "Proceed."}},
        }
        sync_job_result(db, execution=execution, status="Completed", payload=payload)

        from app.models.property_analysis_report import PropertyAnalysisReport
        report = db.query(PropertyAnalysisReport).filter(
            PropertyAnalysisReport.workflow_execution_id == execution.execution_id
        ).first()
        assert float(report.estimate_low) == 25000
        assert report.recommendation == "Proceed."

    def test_malformed_output_produces_fallback_section_and_preserves_raw(self, db, execution):
        payload = {"version": "9.9.9", "results": {"totally_unexpected_key": "mystery data"}}
        synced = sync_job_result(db, execution=execution, status="Completed", payload=payload)
        assert synced.status == "Completed"  # still completes; doesn't crash the sync

        from app.models.result_section import ResultSection
        from app.models.workflow_result import WorkflowResult
        result_row = db.query(WorkflowResult).filter(WorkflowResult.execution_id == execution.execution_id).first()
        assert json.loads(result_row.response_json) == {"totally_unexpected_key": "mystery data"}  # raw preserved

        sections = db.query(ResultSection).filter(ResultSection.result_id == result_row.result_id).all()
        assert any(s.section_type == "unrecognized_output" for s in sections)


# ---------------------------------------------------------------------------
# Result-sync failure isolation and retry (via check_workflow_status)
# ---------------------------------------------------------------------------

class TestResultSyncFailureAndRetry:
    def test_sync_failure_after_remote_completion_does_not_mark_failed(self, db, execution, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "ENABLE_WACP_POLLING", True)

        with patch.object(wacp_adapter, "get_job_status", return_value={"job_id": execution.devtools_execution_id, "status": "COMPLETED", "raw_response": {}}):
            with patch.object(wacp_adapter, "get_job_results", side_effect=wacp_adapter.DevToolsClientError("network blip")):
                status = ai_orchestration_service.check_workflow_status(db, execution_id=execution.execution_id)

        db.refresh(execution)
        assert execution.status not in ("Completed", "Failed")
        assert execution.result_sync_error is not None
        assert "network blip" in execution.result_sync_error

    def test_retry_does_not_resubmit_workflow(self, db, execution, monkeypatch):
        """A second check_workflow_status call (the retry mechanism) must
        only re-attempt fetch+sync - never call submit_workflow/
        dispatch_via_wacp again."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "ENABLE_WACP_POLLING", True)

        with patch.object(wacp_adapter, "get_job_status", return_value={"job_id": execution.devtools_execution_id, "status": "COMPLETED", "raw_response": {}}):
            with patch.object(wacp_adapter, "get_job_results", side_effect=wacp_adapter.DevToolsClientError("first failure")):
                ai_orchestration_service.check_workflow_status(db, execution_id=execution.execution_id)

        with patch.object(ai_orchestration_service, "submit_workflow") as mock_submit:
            with patch.object(wacp_adapter, "get_job_status", return_value={"job_id": execution.devtools_execution_id, "status": "COMPLETED", "raw_response": {}}):
                with patch.object(wacp_adapter, "get_job_results", return_value={"raw_response": {"results": {"executive_summary": "Recovered."}}}):
                    status = ai_orchestration_service.check_workflow_status(db, execution_id=execution.execution_id)
            mock_submit.assert_not_called()

        db.refresh(execution)
        assert execution.status == "Completed"
        assert execution.result_sync_error is None  # cleared on successful retry

    def test_successful_sync_clears_prior_error(self, db, execution, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "ENABLE_WACP_POLLING", True)

        with patch.object(wacp_adapter, "get_job_status", return_value={"job_id": execution.devtools_execution_id, "status": "COMPLETED", "raw_response": {}}):
            with patch.object(wacp_adapter, "get_job_results", side_effect=wacp_adapter.DevToolsClientError("boom")):
                ai_orchestration_service.check_workflow_status(db, execution_id=execution.execution_id)
        db.refresh(execution)
        assert execution.result_sync_error is not None

        with patch.object(wacp_adapter, "get_job_status", return_value={"job_id": execution.devtools_execution_id, "status": "COMPLETED", "raw_response": {}}):
            with patch.object(wacp_adapter, "get_job_results", return_value={"raw_response": {"results": {"executive_summary": "OK now."}}}):
                ai_orchestration_service.check_workflow_status(db, execution_id=execution.execution_id)
        db.refresh(execution)
        assert execution.result_sync_error is None
        assert execution.status == "Completed"

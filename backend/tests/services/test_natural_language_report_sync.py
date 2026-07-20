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
    _extract_non_final_json_outputs,
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
    """
    Tests match the WACP results contract verified directly by the
    DEV-TOOLS Platform Team: result_data["outputs"] is a list of
    {"output_type","title","content"} records, content being a
    JSON-encoded string. The Final Property Analysis is identified by
    its own parsed content (presence of "executive_summary"), never by
    array position - the two tests below deliberately place it in both
    positions to prove that.
    """

    @staticmethod
    def _output(output_type, title, content_dict):
        return {"output_type": output_type, "title": title, "content": json.dumps(content_dict)}

    def test_final_analysis_selected_when_listed_after_validation(self):
        validation = self._output("json", "Property Validation", {"is_valid": True})
        final = self._output("json", "Final Property Analysis", {"executive_summary": "Correct.", "conclusion": "Done."})
        result_data = {"outputs": [validation, final]}
        selected = _select_final_output(result_data)
        assert selected["executive_summary"] == "Correct."

    def test_final_analysis_selected_when_listed_before_validation(self):
        """Same data, reversed order - must select the same result,
        proving position is never the deciding factor."""
        validation = self._output("json", "Property Validation", {"is_valid": True})
        final = self._output("json", "Final Property Analysis", {"executive_summary": "Correct.", "conclusion": "Done."})
        result_data = {"outputs": [final, validation]}
        selected = _select_final_output(result_data)
        assert selected["executive_summary"] == "Correct."

    def test_non_json_output_types_ignored(self):
        doc_output = {"output_type": "document", "title": "PDF Report", "content": "not json at all"}
        final = self._output("json", "Final Property Analysis", {"executive_summary": "Correct."})
        result_data = {"outputs": [doc_output, final]}
        selected = _select_final_output(result_data)
        assert selected["executive_summary"] == "Correct."

    def test_unparseable_json_output_skipped_not_crashed(self):
        broken = {"output_type": "json", "title": "Corrupted", "content": "{not valid json"}
        final = self._output("json", "Final Property Analysis", {"executive_summary": "Still found."})
        result_data = {"outputs": [broken, final]}
        selected = _select_final_output(result_data)
        assert selected["executive_summary"] == "Still found."

    def test_legacy_property_analysis_shape_still_supported(self):
        """Predates the verified contract - kept only for backward
        compatibility with any already-persisted historical payload."""
        result_data = {"property_analysis": {"estimate_low": 1000}}
        assert _select_final_output(result_data) is result_data

    def test_legacy_flat_shape_still_supported(self):
        result_data = {"executive_summary": "Summary text.", "conclusion": "Final word."}
        assert _select_final_output(result_data) is result_data

    def test_no_matching_output_returns_input_unchanged(self):
        validation_only = {"outputs": [self._output("json", "Property Validation", {"is_valid": True})]}
        assert _select_final_output(validation_only) == validation_only

    def test_unrecognized_shape_returns_input_unchanged(self):
        result_data = {"something_else_entirely": True}
        assert _select_final_output(result_data) == result_data


class TestExtractNonFinalJsonOutputs:
    @staticmethod
    def _output(output_type, title, content_dict_or_str):
        content = content_dict_or_str if isinstance(content_dict_or_str, str) else json.dumps(content_dict_or_str)
        return {"output_type": output_type, "title": title, "content": content}

    def test_property_validation_captured_separately(self):
        validation = self._output("json", "Property Validation", {"is_valid": True, "issues": []})
        final = self._output("json", "Final Property Analysis", {"executive_summary": "x"})
        extras = _extract_non_final_json_outputs({"outputs": [validation, final]})
        assert len(extras) == 1
        assert extras[0]["title"] == "Property Validation"
        assert json.loads(extras[0]["content"]) == {"is_valid": True, "issues": []}

    def test_final_output_itself_never_duplicated_into_extras(self):
        final = self._output("json", "Final Property Analysis", {"executive_summary": "x"})
        extras = _extract_non_final_json_outputs({"outputs": [final]})
        assert extras == []

    def test_no_outputs_key_returns_empty_list(self):
        assert _extract_non_final_json_outputs({"property_analysis": {}}) == []

    def test_unparseable_extra_output_kept_as_raw_string(self):
        broken = self._output("json", "Malformed Extra", "{not valid json")
        final = self._output("json", "Final Property Analysis", {"executive_summary": "x"})
        extras = _extract_non_final_json_outputs({"outputs": [broken, final]})
        assert len(extras) == 1
        assert extras[0]["content"] == "{not valid json"


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
            "outputs": [
                {"output_type": "json", "title": "Property Validation", "content": json.dumps({"is_valid": True})},
                {"output_type": "json", "title": "Final Property Analysis", "content": json.dumps({
                    "executive_summary": "The property shows strong development potential.",
                    "key_findings": ["Zoning allows mixed use.", "Lot size exceeds minimum."],
                    "business_health": "Financially sound with moderate risk.",
                    "priority_actions": ["File SB-9 application.", "Commission survey."],
                    "recommendations": ["Proceed with duplex conversion."],
                    "conclusion": "Recommended to proceed.",
                })},
            ],
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
        # The Property Validation output is stored separately, never lost.
        assert "supplementary_output" in section_types
        validation_section = [s for s in sections if s.section_type == "supplementary_output"][0]
        assert validation_section.title == "Property Validation"
        assert json.loads(validation_section.content) == {"is_valid": True}

    def test_missing_optional_section_not_persisted(self, db, execution):
        payload = {"outputs": [
            {"output_type": "json", "title": "Final Property Analysis",
             "content": json.dumps({"executive_summary": "Only a summary, nothing else."})},
        ]}
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
        payload = {"outputs": [{"output_type": "json", "title": "Mystery", "content": json.dumps({"totally_unexpected_key": "mystery data"})}]}
        synced = sync_job_result(db, execution=execution, status="Completed", payload=payload)
        assert synced.status == "Completed"  # still completes; doesn't crash the sync

        from app.models.result_section import ResultSection
        from app.models.workflow_result import WorkflowResult
        result_row = db.query(WorkflowResult).filter(WorkflowResult.execution_id == execution.execution_id).first()
        assert json.loads(result_row.response_json) == payload  # complete raw payload preserved

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

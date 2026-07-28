"""
tests/services/test_wacp_1_1_multi_intent.py

AIHOME RC2 - WACP 1.1 / WIM Module V2 platform integration.

Covers the full required test matrix:
  - WACP 1.0 compatibility
  - WACP 1.1 compatibility
  - PROPERTY_ANALYSIS (single intent)
  - IMAGE_DESIGN (as an additional intent)
  - Multiple Business Intents (ordered)
  - Unknown Business Intent (AIHOME does not reject client-side - that is
    DEV-TOOLS' WIM routing decision, surfaced back as a SKIPPED intent in
    results, never a client-side validation rule AIHOME invents)
  - COMPLETED_WITH_WARNINGS (regression - already implemented, retested
    here to confirm no regression from the multi-intent changes)
  - Combined Outputs
  - Workflow Results

Every test here exercises AIHOME's own integration code (wacp_adapter,
ai_orchestration_service, dev_tools_output_flattening,
business_report_builder, result_sync) - never modifies or asserts on
DEV-TOOLS/WACP/SDK internals beyond confirming AIHOME calls them correctly,
per the "consume the platform exactly as published" boundary.
"""
import json
from unittest.mock import patch

import pytest

from app.db.database import SessionLocal
from app.models.project import Project
from app.models.property import Property
from app.models.project_property import ProjectProperty
from app.models.workflow_execution import WorkflowExecution
from app.models.property_analysis_report import PropertyAnalysisReport

from app.services import wacp_adapter
from app.services.ai_orchestration_service import ai_orchestration_service
from app.services.dev_tools_output_flattening import flatten_dev_tools_outputs
from app.services.business_report_builder import build_business_report
from app.services.result_sync import sync_job_result, get_or_build_business_report


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _make_project_and_property(db, suffix):
    proj = Project(project_id=f"PRJ-{suffix}", project_name="RC2 WACP 1.1 Test")
    db.add(proj); db.commit()
    prop = Property(property_uid=f"PROP-{suffix}", address="1 RC2 Test St")
    db.add(prop); db.commit(); db.refresh(prop)
    db.add(ProjectProperty(project_id=f"PRJ-{suffix}", property_id=prop.id)); db.commit()
    return proj, prop


class TestWacpEnvelopeSubmission:
    """Confirms AIHOME's own submission path (ai_orchestration_service ->
    wacp_adapter -> SDK) produces the correct envelope for every scenario,
    captured at the real HTTP-send boundary - not asserted against a
    mock's call args, against the ACTUAL wire-format dict the SDK would
    transmit."""

    def _capture_envelope(self, db, project, property_id, workflow_code, additional_business_intents=None):
        captured = {}
        import wacp.client.http as http_module
        original_post = http_module.HttpClient.post

        def spy_post(self_http, path, *, json_body=None, **kwargs):
            captured['path'] = path
            captured['json_body'] = json_body
            raise RuntimeError("INTENTIONAL_STOP_AFTER_CAPTURE")

        http_module.HttpClient.post = spy_post
        try:
            try:
                ai_orchestration_service.submit_workflow(
                    db, project_id=project.id, property_id=property_id,
                    workflow_code=workflow_code, additional_business_intents=additional_business_intents,
                )
            except Exception:
                pass
        finally:
            http_module.HttpClient.post = original_post
        return captured

    def test_wacp_1_0_compatibility_single_intent_no_additional_field(self, db):
        """WACP 1.0 shape: single business_intent, additional_business_intents
        key genuinely absent (not present-as-null)."""
        proj, prop = _make_project_and_property(db, "W10")
        captured = self._capture_envelope(db, proj, prop.id, "ZONING_ANALYSIS")
        wacp_block = captured['json_body']['wacp']
        assert "business_intent" in wacp_block
        assert "additional_business_intents" not in wacp_block

    def test_property_analysis_single_intent_submission(self, db):
        proj, prop = _make_project_and_property(db, "PA1")
        captured = self._capture_envelope(db, proj, prop.id, "ZONING_ANALYSIS")
        assert captured['json_body']['wacp']['business_intent'] == "PROPERTY_ANALYSIS"
        assert captured['path'] == "/wacp/v1/jobs"

    def test_wacp_1_1_multi_intent_submission_exact_wire_shape(self, db):
        """The central multi-intent test: business_intent stays primary,
        additional_business_intents carries the ordered follow-on list,
        both live inside `wacp`, never `data`."""
        proj, prop = _make_project_and_property(db, "MULTI")
        captured = self._capture_envelope(
            db, proj, prop.id, "ZONING_ANALYSIS",
            additional_business_intents=["IMAGE_DESIGN", "RENOVATION_PLANNER"],
        )
        wacp_block = captured['json_body']['wacp']
        data_block = captured['json_body']['data']
        assert wacp_block["business_intent"] == "PROPERTY_ANALYSIS"
        assert wacp_block["additional_business_intents"] == ["IMAGE_DESIGN", "RENOVATION_PLANNER"]
        assert "additional_business_intents" not in data_block
        assert "business_intent" not in data_block

    def test_additional_business_intents_persisted_to_execution_record(self, db):
        """AIHOME's own audit record - independent of what DEV-TOOLS does
        with the request."""
        proj, prop = _make_project_and_property(db, "PERSIST")
        import wacp.client.http as http_module
        original_post = http_module.HttpClient.post
        http_module.HttpClient.post = lambda self, path, **kw: (_ for _ in ()).throw(RuntimeError("stop"))
        try:
            try:
                ai_orchestration_service.submit_workflow(
                    db, project_id=proj.id, property_id=prop.id, workflow_code="ZONING_ANALYSIS",
                    additional_business_intents=["IMAGE_DESIGN"],
                )
            except Exception:
                pass
        finally:
            http_module.HttpClient.post = original_post

        execution = db.query(WorkflowExecution).filter(WorkflowExecution.project_id == proj.id).first()
        assert execution is not None
        assert execution.additional_business_intents == ["IMAGE_DESIGN"]

    def test_existing_single_intent_callers_completely_unaffected(self, db):
        """Regression guard: a caller that never passes
        additional_business_intents (every existing caller) must produce
        an execution record with that column NULL, and a wire envelope
        with no trace of the new field."""
        proj, prop = _make_project_and_property(db, "UNAFFECTED")
        captured = self._capture_envelope(db, proj, prop.id, "ZONING_ANALYSIS")
        assert "additional_business_intents" not in captured['json_body']['wacp']

        execution = db.query(WorkflowExecution).filter(WorkflowExecution.project_id == proj.id).first()
        assert execution.additional_business_intents is None


class TestIngestionOfWacp11ResultShapes:
    """dev_tools_output_flattening's recognition of combined_outputs /
    workflow_results / outputs - already covered by direct unit tests in
    the implementation session; re-verified here as part of the full
    matrix, plus the FULL pipeline through business_report_builder."""

    def test_combined_outputs_flattens_with_provenance(self):
        result_data = {"combined_outputs": [
            {"business_intent": "PROPERTY_ANALYSIS", "output_type": "json", "title": "PA",
             "content": json.dumps({"executive_summary": "PA result."})},
            {"business_intent": "IMAGE_DESIGN", "output_type": "json", "title": "ID",
             "content": json.dumps({"summary": "Design result."})},
        ]}
        flattened = flatten_dev_tools_outputs(result_data)
        assert len(flattened) == 2
        assert flattened[0]["business_intent"] == "PROPERTY_ANALYSIS"
        assert flattened[1]["business_intent"] == "IMAGE_DESIGN"

    def test_workflow_results_flattens_as_fallback(self):
        result_data = {"combined_outputs": [], "workflow_results": [
            {"business_intent": "RENOVATION_PLANNER", "outputs": [
                {"output_type": "json", "title": "RP", "content": json.dumps({"summary": "Plan."})}
            ]},
        ]}
        flattened = flatten_dev_tools_outputs(result_data)
        assert len(flattened) == 1
        assert flattened[0]["business_intent"] == "RENOVATION_PLANNER"

    def test_outputs_alias_still_works_when_neither_present(self):
        result_data = {"outputs": [{"output_type": "json", "title": "Legacy", "content": json.dumps({"executive_summary": "Legacy."})}]}
        flattened = flatten_dev_tools_outputs(result_data)
        assert len(flattened) == 1

    def test_unknown_business_intent_does_not_break_ingestion(self):
        """AIHOME never rejects an unknown intent client-side - if
        DEV-TOOLS reports one (however it chooses to represent a
        SKIPPED intent in the result), ingestion must not crash. This
        simulates a combined_outputs entry from an intent AIHOME's own
        local mapping table doesn't recognize - the flattening layer
        doesn't care, since it only reads structure, never validates
        business_intent values against any AIHOME-side allowlist."""
        result_data = {"combined_outputs": [
            {"business_intent": "SOME_FUTURE_INTENT_AIHOME_DOESNT_KNOW", "output_type": "json",
             "title": "Unknown intent output", "content": json.dumps({"summary": "Still processed."})},
        ]}
        flattened = flatten_dev_tools_outputs(result_data)
        assert len(flattened) == 1
        assert flattened[0]["business_intent"] == "SOME_FUTURE_INTENT_AIHOME_DOESNT_KNOW"

    def test_full_pipeline_combined_outputs_to_business_report(self):
        """End-to-end: WACP 1.1 combined_outputs -> normalized Business
        Report, with merged recommendations from both intents and
        provenance in metadata."""
        result_data = {"combined_outputs": [
            {"business_intent": "PROPERTY_ANALYSIS", "output_type": "json", "title": "PA",
             "content": json.dumps({
                 "executive_summary": "Strong renovation candidate.",
                 "recommendations": ["Proceed with design phase"],
             })},
            {"business_intent": "IMAGE_DESIGN", "output_type": "json", "title": "ID",
             "content": json.dumps({"summary": "Farmhouse concept.", "recommendations": ["Consider white oak flooring"]})},
        ]}
        report = build_business_report(result_data, report_type="PROPERTY_ANALYSIS")
        assert report is not None
        assert report["metadata"]["business_intents"] == ["PROPERTY_ANALYSIS", "IMAGE_DESIGN"]
        recs_section = next(s for s in report["sections"] if s["type"] == "recommendations")
        assert "Proceed with design phase" in recs_section["items"]
        assert "Consider white oak flooring" in recs_section["items"]

    def test_single_intent_report_has_no_business_intents_metadata(self):
        result_data = {"outputs": [{"output_type": "json", "title": "X", "content": json.dumps({"executive_summary": "Single."})}]}
        report = build_business_report(result_data, report_type="PROPERTY_ANALYSIS")
        assert "business_intents" not in report["metadata"]


class TestFullSyncPipelineWithWacp11Results:
    """result_sync.sync_job_result / get_or_build_business_report with a
    real WACP 1.1-shaped combined_outputs payload, through a real
    execution and database."""

    def _make_execution(self, db, suffix):
        proj, prop = _make_project_and_property(db, suffix)
        execution = WorkflowExecution(
            execution_number=f"EXE-{suffix}", project_id=proj.id, property_id=prop.id,
            workflow_code="PROPERTY_INTELLIGENCE", status="Running", priority="Normal",
        )
        db.add(execution); db.commit(); db.refresh(execution)
        return execution

    def test_completed_with_combined_outputs_syncs_correctly(self, db):
        execution = self._make_execution(db, "SYNC1")
        payload = {"combined_outputs": [
            {"business_intent": "PROPERTY_ANALYSIS", "output_type": "json", "title": "PA",
             "content": json.dumps({
                 "executive_summary": "Combined outputs sync test.",
                 "key_findings": ["A"], "business_health": "Sound.",
                 "priority_actions": ["B"], "recommendations": ["C"], "conclusion": "Proceed.",
             })},
        ]}
        result = sync_job_result(db, execution=execution, status="Completed", payload=payload)
        assert result.status == "Completed"
        report = db.query(PropertyAnalysisReport).filter(
            PropertyAnalysisReport.workflow_execution_id == execution.execution_id
        ).first()
        assert report is not None
        assert report.report_json["executive_summary"] == "Combined outputs sync test."

    def test_completed_with_warnings_multi_intent_regression(self, db):
        """Regression: COMPLETED_WITH_WARNINGS (from the prior
        compatibility update) still works correctly now that
        flatten_dev_tools_outputs also recognizes combined_outputs -
        a partially-resolved multi-intent plan (some intents skipped)
        is exactly the scenario that produces this status per WIM
        Module V2's own documented ordering/failure behavior."""
        execution = self._make_execution(db, "SYNC2")
        payload = {"combined_outputs": [
            {"business_intent": "PROPERTY_ANALYSIS", "output_type": "json", "title": "PA",
             "content": json.dumps({
                 "executive_summary": "One intent succeeded, one was skipped.",
                 "key_findings": ["A"], "business_health": "Sound.",
                 "priority_actions": ["B"], "recommendations": ["C"], "conclusion": "Proceed.",
             })},
        ]}
        result = sync_job_result(db, execution=execution, status="Completed with Warnings", payload=payload)
        assert result.status == "Completed with Warnings"
        assert result.status != "Failed"
        report = db.query(PropertyAnalysisReport).filter(
            PropertyAnalysisReport.workflow_execution_id == execution.execution_id
        ).first()
        assert report is not None

    def test_get_or_build_rebuilds_historical_combined_outputs_result(self, db):
        """The lazy-build path (from the prior architecture
        improvement) also works transparently for the new WACP 1.1
        result shapes - a historical job stored before this upgrade,
        if it happened to already contain combined_outputs (e.g.
        re-synced from a real DEV-TOOLS response), rebuilds correctly
        on demand."""
        from app.models.workflow_result import WorkflowResult
        execution = self._make_execution(db, "SYNC3")
        payload = {"combined_outputs": [
            {"business_intent": "RENOVATION_PLANNER", "output_type": "json", "title": "RP",
             "content": json.dumps({"executive_summary": "Lazy rebuild of combined_outputs."})},
        ]}
        result_obj = WorkflowResult(
            execution_id=execution.execution_id, result_type="PROPERTY_INTELLIGENCE",
            result_version="1.1", response_json=json.dumps(payload), normalized=1,
        )
        db.add(result_obj); db.commit(); db.refresh(result_obj)

        report = get_or_build_business_report(db, workflow_result_id=result_obj.result_id)
        assert report is not None
        assert report["executive_summary"] == "Lazy rebuild of combined_outputs."
        assert report["metadata"]["business_intents"] == ["RENOVATION_PLANNER"]


class TestCancelledAndFailedUnaffected:
    """Confirms FAILED and CANCELLED handling is completely unaffected by
    every change in this upgrade - the required matrix's final two rows."""

    def _make_execution(self, db, suffix):
        proj, prop = _make_project_and_property(db, suffix)
        execution = WorkflowExecution(
            execution_number=f"EXE-{suffix}", project_id=proj.id, property_id=prop.id,
            workflow_code="PROPERTY_INTELLIGENCE", status="Running", priority="Normal",
        )
        db.add(execution); db.commit(); db.refresh(execution)
        return execution

    def test_failed_unaffected(self, db):
        execution = self._make_execution(db, "FAILREG")
        result = sync_job_result(db, execution=execution, status="Failed", payload={"error_message": "x"})
        assert result.status == "Failed"

    def test_cancelled_unaffected(self, db):
        execution = self._make_execution(db, "CANCELREG")
        result = sync_job_result(db, execution=execution, status="Cancelled", payload={"error_message": "x"})
        assert result.status == "Failed"  # documented pre-existing behavior, unchanged

"""
tests/services/test_wim_v2_result_sync.py

result_sync.py's _select_final_output() and _extract_non_final_json_outputs()
now transparently support DEV-TOOLS' WIM Module V2 merged JSON structure
(a single wrapper output whose content holds a `workflows` list of nested
outputs), alongside the legacy flat-output shape - via the shared
_flatten_dev_tools_outputs() helper. Verifies:

- A real WIM V2 job creates PropertyAnalysisReport + NL ResultSections
  correctly, exactly as the legacy shape always has.
- Every non-final agent output in a WIM V2 job is preserved as a
  supplementary_output section, not silently discarded.
- The legacy flat 2-output shape is completely unaffected (regression).
- Malformed WIM V2 structures (unparseable wrapper content, a workflow
  entry missing its own outputs list) degrade gracefully, never raise.
- This module never reads workflow_code, role, execution_order,
  execution_mode, workflow_template_id, or workflow_run_id anywhere in
  the flattening/selection path.
"""
import json

import pytest

from app.db.database import SessionLocal
from app.models.project import Project
from app.models.property import Property
from app.models.project_property import ProjectProperty
from app.models.workflow_execution import WorkflowExecution
from app.models.property_analysis_report import PropertyAnalysisReport
from app.models.result_section import ResultSection
from app.models.workflow_result import WorkflowResult
from app.services.result_sync import sync_job_result, _select_final_output
from app.services.dev_tools_output_flattening import flatten_dev_tools_outputs as _flatten_dev_tools_outputs


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_execution(db, suffix, workflow_code="PROPERTY_INTELLIGENCE"):
    proj = Project(project_id=f"PRJ-{suffix}", project_name="WIM V2 Sync Test")
    db.add(proj); db.commit()
    prop = Property(property_uid=f"PROP-{suffix}", address="1 WIM V2 Test St")
    db.add(prop); db.commit(); db.refresh(prop)
    db.add(ProjectProperty(project_id=f"PRJ-{suffix}", property_id=prop.id)); db.commit()
    execution = WorkflowExecution(
        execution_number=f"EXE-{suffix}", project_id=proj.id, property_id=prop.id,
        workflow_code=workflow_code, status="Running", priority="Normal",
    )
    db.add(execution); db.commit(); db.refresh(execution)
    return execution


def _wim_v2_payload(child_outputs):
    """Builds a minimal, structurally-real WIM V2 merged payload: one
    entry workflow whose own output is the Final Property Analysis, plus
    however many child workflow outputs the caller supplies."""
    entry_outputs = [{
        "output_id": "entry-1", "title": "Agent Output for entry",
        "output_type": "json", "content_format": "text",
        "content": json.dumps({
            "executive_summary": "WIM V2 test summary.",
            "key_findings": ["Finding A"], "business_health": "Sound.",
            "priority_actions": ["Action A"], "recommendations": ["Rec A"], "conclusion": "Proceed.",
        }),
    }]
    workflows = [{"workflow_run_id": "entry-run", "role": "entry", "status": "completed", "outputs": entry_outputs}]
    for i, child in enumerate(child_outputs):
        workflows.append({
            "workflow_run_id": f"child-run-{i}", "workflow_code": f"WF_CHILD_{i}",
            "role": "child", "status": "completed", "execution_order": i + 1,
            "outputs": [child],
        })
    merged = {"wim_module_version": "2", "entry_workflow_run_id": "entry-run", "workflows": workflows}
    return {"outputs": [{
        "output_id": "wrapper-1", "output_type": "json", "title": "WIM Module V2 Merged Workflow Output",
        "content": json.dumps(merged),
    }]}


class TestWimV2FlattensCorrectly:
    def test_flattens_entry_and_child_outputs_into_one_list(self):
        payload = _wim_v2_payload([
            {"output_id": "c1", "title": "Damage Detection Output", "output_type": "json", "content": json.dumps({"summary": "ok"})},
            {"output_id": "c2", "title": "Room Classification Output", "output_type": "json", "content": json.dumps({"room_type": "kitchen"})},
        ])
        flattened = _flatten_dev_tools_outputs(payload)
        titles = [o["title"] for o in flattened]
        assert titles == ["Agent Output for entry", "Damage Detection Output", "Room Classification Output"]

    def test_legacy_flat_shape_passes_through_unchanged(self):
        legacy = {"outputs": [
            {"output_type": "json", "title": "Property Validation", "content": json.dumps({"validation_status": "ok"})},
            {"output_type": "json", "title": "Final Property Analysis", "content": json.dumps({"executive_summary": "Legacy."})},
        ]}
        flattened = _flatten_dev_tools_outputs(legacy)
        assert flattened == legacy["outputs"]

    def test_select_final_output_finds_entry_output_inside_wim_v2(self):
        payload = _wim_v2_payload([])
        final = _select_final_output(payload)
        assert final["executive_summary"] == "WIM V2 test summary."

    def test_malformed_wrapper_content_does_not_raise(self):
        payload = {"outputs": [{"output_type": "json", "title": "Wrapper", "content": "{not valid json"}]}
        assert _flatten_dev_tools_outputs(payload) == [{"output_type": "json", "title": "Wrapper", "content": "{not valid json"}]

    def test_workflow_missing_outputs_key_is_skipped_not_fatal(self):
        payload = {"outputs": [{"output_type": "json", "title": "Wrapper", "content": json.dumps({
            "workflows": [{"workflow_run_id": "x", "role": "entry"}]  # no "outputs" key
        })}]}
        assert _flatten_dev_tools_outputs(payload) == []

    def test_never_reads_orchestration_fields(self):
        """The flattened output dicts must contain ONLY output_type/title/
        content - never role, workflow_code, execution_order,
        execution_mode, workflow_template_id, or workflow_run_id, even
        though the source payload carries all of them on each workflow
        entry."""
        payload = _wim_v2_payload([
            {"output_id": "c1", "title": "Child Output", "output_type": "json", "content": json.dumps({"x": 1})},
        ])
        flattened = _flatten_dev_tools_outputs(payload)
        for output in flattened:
            assert set(output.keys()) <= {"output_type", "title", "content"}


class TestWimV2FullSyncIntegration:
    def test_wim_v2_job_creates_property_analysis_report(self, db):
        execution = _make_execution(db, "WV2-1")
        payload = _wim_v2_payload([
            {"output_id": "c1", "title": "Damage Detection Output", "output_type": "json", "content": json.dumps({"summary": "no access"})},
        ])
        sync_job_result(db, execution=execution, status="Completed", payload=payload)

        report = db.query(PropertyAnalysisReport).filter(
            PropertyAnalysisReport.workflow_execution_id == execution.execution_id
        ).first()
        assert report is not None
        assert report.report_json["executive_summary"] == "WIM V2 test summary."

    def test_wim_v2_job_preserves_child_outputs_as_supplementary_sections(self, db):
        execution = _make_execution(db, "WV2-2")
        payload = _wim_v2_payload([
            {"output_id": "c1", "title": "Damage Detection Output", "output_type": "json", "content": json.dumps({"summary": "ok"})},
            {"output_id": "c2", "title": "Room Classification Output", "output_type": "json", "content": json.dumps({"room_type": "kitchen"})},
        ])
        sync_job_result(db, execution=execution, status="Completed", payload=payload)

        sections = db.query(ResultSection).join(
            WorkflowResult, ResultSection.result_id == WorkflowResult.result_id
        ).filter(WorkflowResult.execution_id == execution.execution_id).all()
        supplementary_titles = [s.title for s in sections if s.section_type == "supplementary_output"]
        assert "Damage Detection Output" in supplementary_titles
        assert "Room Classification Output" in supplementary_titles

    def test_legacy_shape_still_works_after_wim_v2_support_added(self, db):
        """Direct regression guard: adding WIM V2 support must not change
        legacy-shape behavior in any way."""
        execution = _make_execution(db, "LEGACY-REGRESSION", workflow_code="PROPERTY_ANALYSIS")
        legacy_payload = {"outputs": [
            {"output_type": "json", "title": "Property Validation", "content": json.dumps({"validation_status": "ok"})},
            {"output_type": "json", "title": "Final Property Analysis", "content": json.dumps({
                "executive_summary": "Legacy regression check.",
                "key_findings": ["A"], "business_health": "Sound.",
                "priority_actions": ["B"], "recommendations": ["C"], "conclusion": "Proceed.",
            })},
        ]}
        sync_job_result(db, execution=execution, status="Completed", payload=legacy_payload)

        report = db.query(PropertyAnalysisReport).filter(
            PropertyAnalysisReport.workflow_execution_id == execution.execution_id
        ).first()
        assert report is not None
        assert report.report_json["executive_summary"] == "Legacy regression check."

    def test_malformed_wim_v2_payload_does_not_raise(self, db):
        execution = _make_execution(db, "WV2-MALFORMED")
        malformed = {"outputs": [{"output_type": "json", "title": "Wrapper", "content": json.dumps({
            "workflows": [{"workflow_run_id": "x"}]
        })}]}
        # Must complete without raising - falls through to the
        # unrecognized-output fallback section, same as any other
        # unrecognized payload shape.
        sync_job_result(db, execution=execution, status="Completed", payload=malformed)

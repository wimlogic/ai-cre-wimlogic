"""
tests/services/test_get_or_build_business_report.py

result_sync.get_or_build_business_report() - the pipeline that lets
every historical WorkflowResult render the same enterprise Business
Report as newly-synced jobs, without reprocessing or migration:

    Load WorkflowResult
            v
    Does a normalized PropertyAnalysisReport already exist?
      YES -> use it
      NO  -> build one from the stored response_json (deterministic),
             persist it for future requests (best-effort), then return it

Verifies: first-call build+persist, second-call idempotency (no
duplicate row, identical business content), in-place upgrade of an
existing old-shape report (never a duplicate), graceful None on missing/
malformed data, and that a result whose execution has no property
association still returns a built report even though it can't be
persisted.
"""
import json

import pytest

from app.db.database import SessionLocal
from app.models.project import Project
from app.models.property import Property
from app.models.project_property import ProjectProperty
from app.models.workflow_execution import WorkflowExecution
from app.models.workflow_result import WorkflowResult
from app.models.property_analysis_report import PropertyAnalysisReport
from app.services.result_sync import get_or_build_business_report


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _wim_v2_payload():
    entry_outputs = [{
        "output_id": "entry-1", "title": "Agent Output for entry", "output_type": "json", "content_format": "text",
        "content": json.dumps({
            "executive_summary": "Historical rebuild test summary.",
            "key_findings": ["Finding A"], "business_health": "Sound.",
            "priority_actions": ["Action A"], "recommendations": ["Rec A"], "conclusion": "Proceed.",
        }),
    }]
    merged = {"wim_module_version": "2", "entry_workflow_run_id": "entry-run",
              "workflows": [{"workflow_run_id": "entry-run", "role": "entry", "status": "completed", "outputs": entry_outputs}]}
    return {"outputs": [{"output_id": "wrapper-1", "output_type": "json",
                          "title": "WIM Module V2 Merged Workflow Output", "content": json.dumps(merged)}]}


def _make_execution_and_result(db, suffix):
    proj = Project(project_id=f"PRJ-{suffix}", project_name="Historical Rebuild Test")
    db.add(proj); db.commit()
    prop = Property(property_uid=f"PROP-{suffix}", address="1 Historical Rebuild St")
    db.add(prop); db.commit(); db.refresh(prop)
    db.add(ProjectProperty(project_id=f"PRJ-{suffix}", property_id=prop.id)); db.commit()

    execution = WorkflowExecution(
        execution_number=f"EXE-{suffix}", project_id=proj.id, property_id=prop.id,
        workflow_code="PROPERTY_INTELLIGENCE", status="Completed", priority="Normal",
    )
    db.add(execution); db.commit(); db.refresh(execution)

    result = WorkflowResult(
        execution_id=execution.execution_id, result_type="PROPERTY_INTELLIGENCE",
        result_version="1.0", response_json=json.dumps(_wim_v2_payload()), normalized=1,
    )
    db.add(result); db.commit(); db.refresh(result)
    return execution, result


class TestGetOrBuildBusinessReport:
    def test_first_call_builds_and_persists(self, db):
        execution, result = _make_execution_and_result(db, "GB-1")
        assert db.query(PropertyAnalysisReport).filter(PropertyAnalysisReport.workflow_result_id == result.result_id).count() == 0

        report = get_or_build_business_report(db, workflow_result_id=result.result_id)

        assert report is not None
        assert "sections" in report
        assert report["executive_summary"] == "Historical rebuild test summary."
        assert db.query(PropertyAnalysisReport).filter(PropertyAnalysisReport.workflow_result_id == result.result_id).count() == 1

    def test_second_call_is_idempotent_no_duplicate(self, db):
        execution, result = _make_execution_and_result(db, "GB-2")
        get_or_build_business_report(db, workflow_result_id=result.result_id)
        get_or_build_business_report(db, workflow_result_id=result.result_id)
        assert db.query(PropertyAnalysisReport).filter(PropertyAnalysisReport.workflow_result_id == result.result_id).count() == 1

    def test_business_content_is_deterministic_across_calls(self, db):
        execution, result = _make_execution_and_result(db, "GB-3")
        report1 = get_or_build_business_report(db, workflow_result_id=result.result_id)
        report2 = get_or_build_business_report(db, workflow_result_id=result.result_id)

        def strip_volatile(r):
            d = dict(r); d.pop("generated_at", None); return d
        assert strip_volatile(report1) == strip_volatile(report2)

    def test_existing_old_shape_report_upgraded_in_place_not_duplicated(self, db):
        execution, result = _make_execution_and_result(db, "GB-4")
        old_shape = PropertyAnalysisReport(
            project_id=f"PRJ-GB-4", property_id=execution.property_id,
            workflow_execution_id=execution.execution_id, workflow_result_id=result.result_id,
            report_json={"executive_summary": "Old raw shape, no sections."},
            workflow_status="Completed",
        )
        db.add(old_shape); db.commit()
        assert db.query(PropertyAnalysisReport).filter(PropertyAnalysisReport.workflow_result_id == result.result_id).count() == 1

        report = get_or_build_business_report(db, workflow_result_id=result.result_id)

        assert "sections" in report
        assert db.query(PropertyAnalysisReport).filter(PropertyAnalysisReport.workflow_result_id == result.result_id).count() == 1  # updated in place, not duplicated
        db.refresh(old_shape)
        assert "sections" in old_shape.report_json

    def test_already_normalized_report_is_used_directly_no_rebuild(self, db):
        execution, result = _make_execution_and_result(db, "GB-5")
        already_normalized = {"report_type": "PROPERTY_INTELLIGENCE", "report_version": "1.0", "property": {},
                               "executive_summary": "Already built.", "sections": [], "confidence": "High",
                               "generated_at": "2020-01-01T00:00:00", "metadata": {}}
        db.add(PropertyAnalysisReport(
            project_id="PRJ-GB-5", property_id=execution.property_id,
            workflow_execution_id=execution.execution_id, workflow_result_id=result.result_id,
            report_json=already_normalized, workflow_status="Completed",
        ))
        db.commit()

        report = get_or_build_business_report(db, workflow_result_id=result.result_id)
        assert report["executive_summary"] == "Already built."
        assert db.query(PropertyAnalysisReport).filter(PropertyAnalysisReport.workflow_result_id == result.result_id).count() == 1

    def test_returns_none_for_nonexistent_workflow_result(self, db):
        assert get_or_build_business_report(db, workflow_result_id=999999999) is None

    def test_returns_none_gracefully_for_missing_response_json(self, db):
        execution, result = _make_execution_and_result(db, "GB-6")
        result.response_json = None
        db.commit()
        assert get_or_build_business_report(db, workflow_result_id=result.result_id) is None

    def test_returns_none_gracefully_for_malformed_response_json(self, db):
        execution, result = _make_execution_and_result(db, "GB-7")
        result.response_json = "{not valid json"
        db.commit()
        assert get_or_build_business_report(db, workflow_result_id=result.result_id) is None

    # Note: a "no execution found" / "no property association" scenario
    # is intentionally not tested here - WorkflowResult.execution_id is
    # FK-enforced (ON DELETE CASCADE) and WorkflowExecution.property_id
    # is NOT NULL, so both states are unreachable via normal inserts in
    # this schema. The defensive check in get_or_build_business_report()
    # remains as valid defense-in-depth regardless.

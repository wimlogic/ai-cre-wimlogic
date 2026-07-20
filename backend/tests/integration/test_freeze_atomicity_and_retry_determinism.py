"""
tests/integration/test_freeze_atomicity_and_retry_determinism.py

AI HOME Knowledge Inheritance V1.0 - Step 6 (Verify Atomic Freeze) and
Step 7 (Verify Execution and Retry) verification tests.

These are deliberately adversarial: they force real failures and real
post-Submit source-data changes, rather than only asserting the happy
path, since that is the only way to actually prove atomicity and
immutability rather than merely assert it.
"""
import datetime
from unittest.mock import patch

import pytest

from app.db.database import SessionLocal
from app.models.project import Project
from app.models.project_property import ProjectProperty
from app.models.property import Property
from app.models.property_image import PropertyImage
from app.models.property_analysis_report import PropertyAnalysisReport
from app.models.design_tool_knowledge_rule import DesignToolKnowledgeRule

from app import crud
from app.schemas.design_job import DesignJobCreate, DesignJobConfigureImageItem
from app.schemas.design_tool import DesignToolCreate
from app.schemas.design_tool_image_requirement import DesignToolImageRequirementCreate
from app.schemas.workflow_execution import WorkflowExecutionUpdate
from app.services.design_job_service import design_job_service, DesignJobValidationError
from app.services.design_job_execution_service import design_job_execution_service
from app.services import wacp_adapter, payload_builder


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _base_scenario(db, suffix):
    proj = Project(project_id=f"PRJ-{suffix}", project_name="Freeze Test Project", description="Original description.")
    db.add(proj)
    db.commit()

    prop = Property(property_uid=f"PROP-{suffix}", address="1 Freeze St", notes="Original notes.")
    db.add(prop)
    db.commit()
    db.refresh(prop)

    db.add(ProjectProperty(project_id=proj.project_id, property_id=prop.id))
    db.commit()

    tool = crud.design_tool.create(db, obj_in=DesignToolCreate(
        tool_code=f"TOOL-{suffix}", tool_name="Freeze Tool", design_type="image_creation", workflow_code="WF_FREEZE",
    ))
    crud.design_tool_image_requirement.create(db, obj_in=DesignToolImageRequirementCreate(
        tool_id=tool.id, input_role="primary", min_count=1, max_count=1,
    ))
    for scope in ("project", "property", "image"):
        db.add(DesignToolKnowledgeRule(tool_id=tool.id, knowledge_scope=scope, is_required=0, include_in_context=1))
    db.commit()

    img = PropertyImage(property_id=prop.id, image_type="uploaded", image_role="primary", is_primary=1,
                         notes="Original image notes.", image_url=f"https://example.com/{suffix}.jpg")
    db.add(img)
    db.commit()
    db.refresh(img)

    job = design_job_service.create_design_job(db, DesignJobCreate(
        project_id=proj.project_id, property_id=prop.id, tool_id=tool.id,
    ))
    design_job_service.set_images(db, job_id=job.id, images=[
        DesignJobConfigureImageItem(property_image_id=img.id, input_role="primary"),
    ])
    return proj, prop, tool, img, job


# ---------------------------------------------------------------------------
# Step 6 - Atomic Freeze
# ---------------------------------------------------------------------------

def test_step6_failure_during_context_build_leaves_zero_partial_state(db):
    """
    Force build_design_job_context() to raise partway through Submit.
    Nothing frozen may exist afterward - not effective_context_json, not
    tool_options_json, not submitted_payload_json - and the Job must
    remain Draft.
    """
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    proj, prop, tool, img, job = _base_scenario(db, suffix)

    with patch("app.services.design_job_service.build_design_job_context", side_effect=RuntimeError("forced failure")):
        with pytest.raises(RuntimeError):
            design_job_service.submit_design_job(db, job_id=job.id)

    db.refresh(job)
    assert job.status == "draft"
    assert job.effective_context_json is None
    assert job.tool_options_json is None
    assert job.submitted_payload_json is None


def test_step6_failure_during_media_input_build_leaves_zero_partial_state(db):
    """
    Same guarantee, forcing the failure one step later (media input
    resolution) - proves the atomicity holds regardless of WHICH stage
    inside Submit fails, not just the first one.
    """
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    proj, prop, tool, img, job = _base_scenario(db, suffix)

    with patch("app.services.design_job_service.build_design_job_inputs", side_effect=RuntimeError("forced failure")):
        with pytest.raises(RuntimeError):
            design_job_service.submit_design_job(db, job_id=job.id)

    db.refresh(job)
    assert job.status == "draft"
    assert job.effective_context_json is None
    assert job.tool_options_json is None
    assert job.submitted_payload_json is None


def test_step6_successful_submit_freezes_all_four_together(db):
    """
    Positive case: on a clean Submit, all four frozen artifacts
    (effective_context_json, submitted_payload_json, tool_options_json,
    and the Design Job's own snapshotted Tool selection: tool_code /
    design_type / workflow_code) are present together, from the exact
    same Submit call - not assembled piecemeal across separate calls.
    """
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    proj, prop, tool, img, job = _base_scenario(db, suffix)

    submitted = design_job_service.submit_design_job(db, job_id=job.id)

    assert submitted.status == "submitted"
    assert submitted.effective_context_json is not None
    assert submitted.submitted_payload_json is not None
    assert submitted.tool_options_json is not None
    # Selected Design Tool configuration snapshotted at Create, unchanged
    # by Submit, and present inside the frozen payload too.
    assert submitted.tool_code == tool.tool_code
    assert submitted.design_type == tool.design_type
    assert submitted.workflow_code == tool.workflow_code
    assert submitted.submitted_payload_json["tool_code"] == tool.tool_code

    # Re-submitting an already-submitted Job must be rejected - proves
    # there is exactly one freeze point, not a re-freezable one.
    with pytest.raises(DesignJobValidationError):
        design_job_service.submit_design_job(db, job_id=job.id)


def test_step6_re_submit_after_correcting_error_succeeds(db):
    """
    A failed Submit must not poison the Job - after fixing whatever
    caused the failure, a normal Submit must succeed cleanly.
    """
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    proj, prop, tool, img, job = _base_scenario(db, suffix)

    with patch("app.services.design_job_service.build_design_job_context", side_effect=RuntimeError("forced failure")):
        with pytest.raises(RuntimeError):
            design_job_service.submit_design_job(db, job_id=job.id)

    db.refresh(job)
    assert job.status == "draft"

    submitted = design_job_service.submit_design_job(db, job_id=job.id)
    assert submitted.status == "submitted"
    assert submitted.submitted_payload_json is not None


# ---------------------------------------------------------------------------
# Step 7 - Execution and Retry determinism
# ---------------------------------------------------------------------------

def test_step7_retry_ignores_all_post_submit_source_changes(db):
    """
    The strongest possible retry-determinism test: change EVERY
    inheritable source (Project Description, Property Notes, add a
    newer completed Property Analysis Report, edit the live Image's
    notes/role) after Submit, then Retry - and prove the payload
    actually sent to WACP is byte-for-byte identical to the one
    originally frozen, not merely that certain functions weren't called.
    """
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    proj, prop, tool, img, job = _base_scenario(db, suffix)

    submitted = design_job_service.submit_design_job(db, job_id=job.id)
    frozen_payload_at_submit = submitted.submitted_payload_json

    # Initial execute (fails), to make the job Retry-eligible.
    with patch.object(wacp_adapter, "submit_payload", side_effect=wacp_adapter.DevToolsClientError("simulated failure")):
        try:
            design_job_execution_service.execute_submitted_job(db, job_id=submitted.id)
        except wacp_adapter.DevToolsClientError:
            pass

    # Now change EVERYTHING that could theoretically leak into a rebuilt context.
    proj.description = "CHANGED description - must never appear in retry payload."
    db.add(proj)
    prop.notes = "CHANGED notes - must never appear in retry payload."
    db.add(prop)
    db.add(PropertyAnalysisReport(
        project_id=proj.project_id, property_id=prop.id, workflow_status="Completed",
        completed_at=datetime.datetime.now(), recommendation="CHANGED analysis - must never appear in retry payload.",
    ))
    img.notes = "CHANGED image notes - must never appear in retry payload."
    img.image_role = "kitchen"
    db.add(img)
    db.commit()

    captured = {}

    def capture(data, *, business_intent=None, workflow_code, project_code, priority="NORMAL", correlation_id=None, callback_url=None):
        captured["data"] = data
        return {"job_id": "DEVTOOLS-RETRY", "status": "QUEUED"}

    with patch.object(wacp_adapter, "submit_payload", side_effect=capture):
        design_job_execution_service.retry_design_job(db, job_id=submitted.id)

    # The payload actually sent on retry must be identical to what was
    # frozen at Submit - none of the "CHANGED" strings may appear anywhere.
    import json
    retry_payload_str = json.dumps(captured["data"])
    assert "CHANGED" not in retry_payload_str
    assert json.dumps(captured["data"], sort_keys=True) == json.dumps(frozen_payload_at_submit, sort_keys=True)

    # And the Job's own persisted submitted_payload_json is likewise untouched.
    db.refresh(submitted)
    assert json.dumps(submitted.submitted_payload_json, sort_keys=True) == json.dumps(frozen_payload_at_submit, sort_keys=True)


def test_step7_wacp_submission_continues_using_frozen_payload_on_execute(db):
    """Baseline confirmation that the very first Execute (not just Retry) also uses the frozen payload, not a rebuild."""
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    proj, prop, tool, img, job = _base_scenario(db, suffix)
    submitted = design_job_service.submit_design_job(db, job_id=job.id)

    captured = {}

    def capture(data, *, business_intent=None, workflow_code, project_code, priority="NORMAL", correlation_id=None, callback_url=None):
        captured["data"] = data
        return {"job_id": "DEVTOOLS-EXEC", "status": "QUEUED"}

    with patch("app.services.design_job_service.build_design_job_context") as spy_context:
        with patch.object(wacp_adapter, "submit_payload", side_effect=capture):
            design_job_execution_service.execute_submitted_job(db, job_id=submitted.id)
        spy_context.assert_not_called()

    import json
    assert json.dumps(captured["data"], sort_keys=True) == json.dumps(submitted.submitted_payload_json, sort_keys=True)

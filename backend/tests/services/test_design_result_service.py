"""
tests/services/test_design_result_service.py

AIHOME Phase 1 - tests for design_result_service.py: version creation +
lineage ingestion, and baseline approval (idempotency, supersession,
design_scope derivation, first-approval-for-a-scope correctness).
"""
import datetime

import pytest

from app.db.database import SessionLocal
from app.models.project import Project
from app.models.property import Property
from app.models.property_image import PropertyImage
from app.models.design_tool import DesignTool
from app.models.design_job import DesignJob
from app.models.design_job_image import DesignJobImage
from app.models.workflow_execution import WorkflowExecution
from app.crud.design_image_lineage import design_image_lineage as crud_lineage
from app.crud.approved_design_baseline import approved_design_baseline as crud_baseline

from app.services.design_result_service import (
    create_design_image_version,
    approve_design_version,
    DesignResultError,
)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_scenario(db, suffix, image_role="kitchen"):
    proj = Project(project_id=f"PRJ-{suffix}", project_name="Design Result Test")
    db.add(proj); db.commit()

    prop = Property(property_uid=f"PROP-{suffix}", address="1 Design Result St")
    db.add(prop); db.commit(); db.refresh(prop)

    img = PropertyImage(property_id=prop.id, image_type="uploaded", image_role=image_role,
                         is_primary=1, image_url=f"https://example.com/{suffix}.jpg")
    db.add(img); db.commit(); db.refresh(img)

    tool = DesignTool(tool_code=f"TOOL-{suffix}", tool_name="Test Tool",
                       design_type="image_creation", workflow_code="WF_DESIGN_STUDIO")
    db.add(tool); db.commit(); db.refresh(tool)

    job = DesignJob(
        job_number=f"DSJ-{suffix}", project_id=proj.project_id, property_id=prop.id, tool_id=tool.id,
        tool_code=tool.tool_code, design_type=tool.design_type, workflow_code=tool.workflow_code,
        tool_options_json={"design_style": "Modern"}, effective_context_json={"x": 1},
        submitted_payload_json={"job_number": f"DSJ-{suffix}"}, status="completed",
    )
    db.add(job); db.commit(); db.refresh(job)

    db.add(DesignJobImage(design_job_id=job.id, property_image_id=img.id, input_role="primary"))
    db.commit()

    wf_exec = WorkflowExecution(
        execution_number=f"EXE-{suffix}", project_id=proj.id, property_id=prop.id,
        workflow_code="WF_DESIGN_STUDIO", status="Completed", priority="Normal",
        completed_at=datetime.datetime.now(),
    )
    db.add(wf_exec); db.commit(); db.refresh(wf_exec)

    return {"project": proj, "property": prop, "image": img, "tool": tool, "job": job, "workflow_execution": wf_exec}


def _suffix():
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")


class TestCreateDesignImageVersion:
    def test_first_version_is_number_one(self, db):
        s = _make_scenario(db, _suffix())
        version = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="properties/1/images/1/versions/v1.jpg",
            source_property_image_ids=[s["image"].id],
        )
        assert version.version_number == 1
        assert version.status == "generated"

    def test_version_numbers_increment_monotonically(self, db):
        s = _make_scenario(db, _suffix())
        v1 = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        v2 = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v2.jpg", storage_path="p/v2.jpg", source_property_image_ids=[s["image"].id],
        )
        assert v1.version_number == 1
        assert v2.version_number == 2

    def test_lineage_row_created_for_source_property_image(self, db):
        s = _make_scenario(db, _suffix())
        version = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        rows, count = crud_lineage.get_multi(db, image_version_id=version.id)
        assert count == 1
        assert rows[0].source_type == "property_image"
        assert rows[0].source_property_image_id == s["image"].id

    def test_lineage_row_created_for_refinement_of_prior_version(self, db):
        s = _make_scenario(db, _suffix())
        v1 = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        v2 = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v2.jpg", storage_path="p/v2.jpg", source_image_version_ids=[v1.id],
        )
        rows, count = crud_lineage.get_multi(db, image_version_id=v2.id)
        assert count == 1
        assert rows[0].source_type == "image_version"
        assert rows[0].source_image_version_id == v1.id

    def test_multiple_lineage_sources_all_recorded(self, db):
        s = _make_scenario(db, _suffix())
        version = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg",
            source_property_image_ids=[s["image"].id],
        )
        v2 = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v2.jpg", storage_path="p/v2.jpg",
            source_property_image_ids=[s["image"].id], source_image_version_ids=[version.id],
        )
        rows, count = crud_lineage.get_multi(db, image_version_id=v2.id)
        assert count == 2


class TestApproveDesignVersion:
    def test_first_approval_for_a_scope_succeeds(self, db):
        """The exact case the Property-row lock design fixes: no active
        baseline exists yet for this scope at all."""
        s = _make_scenario(db, _suffix())
        version = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        baseline = approve_design_version(db, image_version_id=version.id)
        assert baseline.status == "active"
        assert baseline.image_version_id == version.id

    def test_design_scope_derived_from_primary_image_role(self, db):
        s = _make_scenario(db, _suffix(), image_role="front_exterior")
        version = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        baseline = approve_design_version(db, image_version_id=version.id)
        assert baseline.design_scope == "front_exterior"

    def test_design_scope_falls_back_to_general_when_no_image_role(self, db):
        s = _make_scenario(db, _suffix(), image_role=None)
        version = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        baseline = approve_design_version(db, image_version_id=version.id)
        assert baseline.design_scope == "general"

    def test_reapproving_same_version_is_idempotent_noop(self, db):
        s = _make_scenario(db, _suffix())
        version = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        baseline_first = approve_design_version(db, image_version_id=version.id)
        baseline_second = approve_design_version(db, image_version_id=version.id)
        assert baseline_first.id == baseline_second.id

        all_baselines, count = crud_baseline.get_multi(db, property_id=s["property"].id)
        assert count == 1  # no duplicate row created

    def test_approving_different_version_supersedes_prior_active(self, db):
        s = _make_scenario(db, _suffix())
        v1 = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        v2 = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v2.jpg", storage_path="p/v2.jpg", source_property_image_ids=[s["image"].id],
        )
        baseline1 = approve_design_version(db, image_version_id=v1.id)
        baseline2 = approve_design_version(db, image_version_id=v2.id)

        db.refresh(baseline1)
        assert baseline1.status == "superseded"
        assert baseline2.status == "active"

        db.refresh(v1)
        db.refresh(v2)
        assert v2.status == "approved"

    def test_exactly_one_active_baseline_per_scope_after_multiple_approvals(self, db):
        s = _make_scenario(db, _suffix())
        for i in range(3):
            version = create_design_image_version(
                db, design_job=s["job"], workflow_execution=s["workflow_execution"],
                file_name=f"v{i}.jpg", storage_path=f"p/v{i}.jpg", source_property_image_ids=[s["image"].id],
            )
            approve_design_version(db, image_version_id=version.id)

        active_baselines, count = crud_baseline.get_multi(db, property_id=s["property"].id, status="active")
        assert count == 1

    def test_nonexistent_version_raises_domain_error(self, db):
        with pytest.raises(DesignResultError):
            approve_design_version(db, image_version_id=999999999)

    def test_baseline_snapshots_design_job_payload_fields(self, db):
        s = _make_scenario(db, _suffix())
        version = create_design_image_version(
            db, design_job=s["job"], workflow_execution=s["workflow_execution"],
            file_name="v1.jpg", storage_path="p/v1.jpg", source_property_image_ids=[s["image"].id],
        )
        baseline = approve_design_version(db, image_version_id=version.id)
        assert baseline.tool_options_json == {"design_style": "Modern"}
        assert baseline.effective_context_json == {"x": 1}
        assert baseline.submitted_payload_json == {"job_number": s["job"].job_number}

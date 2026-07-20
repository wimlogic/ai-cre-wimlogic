"""
tests/integration/test_knowledge_context_extension.py

Knowledge Inheritance Engine Phase 1.2A - Checkpoint 3 integration tests:
field-level rule wiring in build_design_job_context(), and the
Submit-time-fresh image context change. Requires a real database.
"""
import datetime

import pytest

from app.db.database import SessionLocal
from app.models.project import Project
from app.models.project_property import ProjectProperty
from app.models.property import Property
from app.models.property_image import PropertyImage
from app.models.design_tool_knowledge_rule import DesignToolKnowledgeRule

from app import crud
from app.schemas.design_job import DesignJobCreate, DesignJobConfigureImageItem
from app.schemas.design_tool import DesignToolCreate
from app.schemas.design_tool_image_requirement import DesignToolImageRequirementCreate
from app.services.design_job_service import design_job_service
from app.services.payload_builder import build_design_job_context


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def scenario(db):
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")

    proj = Project(project_id=f"PRJ-{suffix}", project_name="1.2A Test Project", description="Base description.")
    db.add(proj)
    db.commit()

    prop = Property(property_uid=f"PROP-{suffix}", address="1 Field Rule St", notes="Base notes.")
    db.add(prop)
    db.commit()
    db.refresh(prop)

    db.add(ProjectProperty(project_id=proj.project_id, property_id=prop.id))
    db.commit()

    tool = crud.design_tool.create(db, obj_in=DesignToolCreate(
        tool_code=f"TOOL-{suffix}", tool_name="1.2A Tool", design_type="image_creation", workflow_code="WF_TEST",
    ))
    crud.design_tool_image_requirement.create(db, obj_in=DesignToolImageRequirementCreate(
        tool_id=tool.id, input_role="primary", min_count=1, max_count=1,
    ))
    for scope in ("project", "property", "image"):
        db.add(DesignToolKnowledgeRule(tool_id=tool.id, knowledge_scope=scope, is_required=0, include_in_context=1))
    db.commit()

    image = PropertyImage(property_id=prop.id, image_type="uploaded", image_role="front_exterior",
                           notes="Original notes.", is_primary=1, image_url=f"https://example.com/{suffix}.jpg")
    db.add(image)
    db.commit()
    db.refresh(image)

    job = design_job_service.create_design_job(db, DesignJobCreate(
        project_id=proj.project_id, property_id=prop.id, tool_id=tool.id,
    ))
    design_job_service.set_images(db, job_id=job.id, images=[
        DesignJobConfigureImageItem(property_image_id=image.id, input_role="primary"),
    ])
    return {"project": proj, "property": prop, "tool": tool, "job": job, "image": image}


def test_field_level_rule_adds_project_goals_alongside_legacy_fields(db, scenario):
    scenario["project"].goals = "Maximize resale value."
    db.add(scenario["project"])
    db.commit()

    db.add(DesignToolKnowledgeRule(tool_id=scenario["tool"].id, knowledge_scope="project", field_code="PROJECT.GOALS", include_in_context=1))
    db.commit()

    job = crud.design_job.get(db, scenario["job"].id)
    job_images, _ = crud.design_job_image.get_multi(db, design_job_id=job.id)
    context = build_design_job_context(db, job=job, job_images=job_images)

    # Legacy fields still present, untouched.
    assert context["project"]["project_id"] == scenario["project"].project_id
    assert context["project"]["description"] == "Base description."
    # New field present alongside them.
    assert context["project"]["goals"] == "Maximize resale value."


def test_without_field_rule_new_field_never_appears_even_if_populated(db, scenario):
    scenario["project"].goals = "Should never appear."
    db.add(scenario["project"])
    db.commit()
    # No PROJECT.GOALS rule added.

    job = crud.design_job.get(db, scenario["job"].id)
    job_images, _ = crud.design_job_image.get_multi(db, design_job_id=job.id)
    context = build_design_job_context(db, job=job, job_images=job_images)

    assert "goals" not in context["project"]


def test_property_field_level_rule(db, scenario):
    scenario["property"].bedrooms = 3
    scenario["property"].bathrooms = 2.5
    db.add(scenario["property"])
    db.commit()
    db.add(DesignToolKnowledgeRule(tool_id=scenario["tool"].id, knowledge_scope="property", field_code="PROPERTY.BEDROOMS", include_in_context=1))
    db.add(DesignToolKnowledgeRule(tool_id=scenario["tool"].id, knowledge_scope="property", field_code="PROPERTY.BATHROOMS", include_in_context=1))
    db.commit()

    job = crud.design_job.get(db, scenario["job"].id)
    job_images, _ = crud.design_job_image.get_multi(db, design_job_id=job.id)
    context = build_design_job_context(db, job=job, job_images=job_images)

    assert context["property"]["bedrooms"] == 3
    assert float(context["property"]["bathrooms"]) == 2.5
    assert context["property"]["notes"] == "Base notes."  # legacy field untouched


def test_image_field_level_rule(db, scenario):
    scenario["image"].camera_direction = "north"
    db.add(scenario["image"])
    db.commit()
    db.add(DesignToolKnowledgeRule(tool_id=scenario["tool"].id, knowledge_scope="image", field_code="IMAGE.CAMERA_DIRECTION", include_in_context=1))
    db.commit()

    job = crud.design_job.get(db, scenario["job"].id)
    job_images, _ = crud.design_job_image.get_multi(db, design_job_id=job.id)
    context = build_design_job_context(db, job=job, job_images=job_images)

    assert context["images"][0]["knowledge"]["camera_direction"] == "north"
    assert context["images"][0]["knowledge"]["image_role"] == "front_exterior"  # legacy field untouched


def test_design_job_scope_omitted_when_no_field_rules(db, scenario):
    job = crud.design_job.get(db, scenario["job"].id)
    job_images, _ = crud.design_job_image.get_multi(db, design_job_id=job.id)
    context = build_design_job_context(db, job=job, job_images=job_images)
    assert "design_job" not in context


def test_design_job_scope_appears_with_field_rule(db, scenario):
    design_job_service.set_tool_options(db, job_id=scenario["job"].id, tool_options={})
    job = crud.design_job.get(db, scenario["job"].id)
    job.job_prompt = "Modernize the exterior."
    db.add(job)
    db.commit()

    db.add(DesignToolKnowledgeRule(tool_id=scenario["tool"].id, knowledge_scope="design_job", field_code="DESIGN_JOB.PROMPT", include_in_context=1))
    db.commit()

    job = crud.design_job.get(db, scenario["job"].id)
    job_images, _ = crud.design_job_image.get_multi(db, design_job_id=job.id)
    context = build_design_job_context(db, job=job, job_images=job_images)

    assert context["design_job"] == {"job_prompt": "Modernize the exterior."}


# ---------------------------------------------------------------------------
# Submit-time-fresh image context (the flagged behavioral change)
# ---------------------------------------------------------------------------

def test_submit_time_fresh_image_context_reflects_post_configure_edit(db, scenario):
    """
    The core new behavior: edit the image's notes AFTER Configure
    (image_knowledge_snapshot_json is already frozen with "Original
    notes.") but BEFORE Submit - the frozen effective_context must
    reflect the EDITED value, not the Configure-time snapshot.
    """
    job_images, _ = crud.design_job_image.get_multi(db, design_job_id=scenario["job"].id)
    assert job_images[0].image_knowledge_snapshot_json["notes"] == "Original notes."  # confirm the old snapshot value

    scenario["image"].notes = "Edited after Configure, before Submit."
    db.add(scenario["image"])
    db.commit()

    job = crud.design_job.get(db, scenario["job"].id)
    context = build_design_job_context(db, job=job, job_images=job_images)

    assert context["images"][0]["knowledge"]["notes"] == "Edited after Configure, before Submit."


def test_configure_time_snapshot_itself_remains_unchanged(db, scenario):
    """image_knowledge_snapshot_json continues to serve its existing
    purposes (Requirement validation, historical record) - it is not
    rewritten by the Submit-time-fresh context change."""
    scenario["image"].notes = "Edited after Configure."
    db.add(scenario["image"])
    db.commit()

    job_images, _ = crud.design_job_image.get_multi(db, design_job_id=scenario["job"].id)
    assert job_images[0].image_knowledge_snapshot_json["notes"] == "Original notes."


def test_submitted_job_effective_context_reflects_live_data_at_submit_time(db, scenario):
    scenario["image"].notes = "Live at Submit time."
    scenario["image"].camera_direction = "south"
    db.add(scenario["image"])
    db.commit()
    db.add(DesignToolKnowledgeRule(tool_id=scenario["tool"].id, knowledge_scope="image", field_code="IMAGE.CAMERA_DIRECTION", include_in_context=1))
    db.commit()

    submitted = design_job_service.submit_design_job(db, job_id=scenario["job"].id)

    assert submitted.effective_context_json["images"][0]["knowledge"]["notes"] == "Live at Submit time."
    assert submitted.effective_context_json["images"][0]["knowledge"]["camera_direction"] == "south"


# ---------------------------------------------------------------------------
# Legacy regression, explicit
# ---------------------------------------------------------------------------

def test_reference_tool_with_only_blanket_rules_unchanged_shape(db, scenario):
    """No field-level rules added anywhere - the full submitted context
    must contain exactly the pre-1.2A keys, nothing more."""
    submitted = design_job_service.submit_design_job(db, job_id=scenario["job"].id)
    ctx = submitted.effective_context_json

    assert set(ctx["project"].keys()) == {"project_id", "project_name", "description", "knowledge_instructions"}
    assert set(ctx["property"].keys()) == {
        "address", "city", "state", "zip", "apn", "zoning_code", "existing_use", "notes", "knowledge_instructions",
    }
    assert set(ctx["images"][0].keys()) == {"property_image_id", "input_role", "knowledge", "knowledge_instructions"}
    assert set(ctx["images"][0]["knowledge"].keys()) == {
        "image_role", "notes", "ai_prompt", "tags", "constraints", "priority", "is_primary", "status",
    }
    assert "design_job" not in ctx

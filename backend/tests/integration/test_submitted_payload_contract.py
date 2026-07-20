"""
tests/integration/test_submitted_payload_contract.py

AI HOME Knowledge Inheritance V1.0 - Step 5 test coverage:
inheritance_04_backend_implementation.md's payload contract assembly in
submit_design_job(), verified against inheritance_05_validation_test_plan.md
§11 "Unit Tests - Submitted Payload" (SP-001 through SP-012).

Requires a real database - Submit resolves the Tool, Project, Property,
Tool Options, Knowledge Rules, and Design Job Images all from the DB.
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
from app.schemas.design_tool_option import DesignToolOptionCreate
from app.schemas.design_tool_image_requirement import DesignToolImageRequirementCreate
from app.services.design_job_service import design_job_service


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_submitted_job(db, *, with_design_style=True, tool_options_overrides=None):
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")

    proj = Project(project_id=f"PRJ-{suffix}", project_name="Test Project", description="Test description.")
    db.add(proj)
    db.commit()

    prop = Property(property_uid=f"PROP-{suffix}", address="1 Test St", notes="Preserve porch.")
    db.add(prop)
    db.commit()
    db.refresh(prop)

    db.add(ProjectProperty(project_id=proj.project_id, property_id=prop.id))
    db.commit()

    tool = crud.design_tool.create(db, obj_in=DesignToolCreate(
        tool_code=f"TOOL-{suffix}", tool_name="Test Tool", design_type="image_creation",
        workflow_code="WF_TEST",
    ))
    # business_purpose / business_instructions aren't part of DesignToolCreate's
    # required fields in every version of this schema - set directly if present.
    if hasattr(tool, "business_purpose"):
        tool.business_purpose = "Create a redesigned exterior concept."
        tool.business_instructions = "Preserve the property identity."
        db.add(tool)
        db.commit()
        db.refresh(tool)

    crud.design_tool_image_requirement.create(db, obj_in=DesignToolImageRequirementCreate(
        tool_id=tool.id, input_role="primary", min_count=1, max_count=1,
    ))

    if with_design_style:
        crud.design_tool_option.create(db, obj_in=DesignToolOptionCreate(
            tool_id=tool.id, option_code="design_style", option_label="Design Style",
            option_type="select", allowed_values_json=["Modern", "Classic"],
            default_value="Modern", is_required=1,
        ))

    for scope in ("project", "property", "image"):
        db.add(DesignToolKnowledgeRule(tool_id=tool.id, knowledge_scope=scope, is_required=0,
                                        include_in_context=1, instructions=f"{scope} instructions"))
    db.commit()

    img = PropertyImage(property_id=prop.id, image_type="uploaded", image_role="primary", is_primary=1,
                         image_url=f"https://example.com/{suffix}.jpg")
    db.add(img)
    db.commit()
    db.refresh(img)

    job = design_job_service.create_design_job(db, DesignJobCreate(
        project_id=proj.project_id, property_id=prop.id, tool_id=tool.id,
    ))
    design_job_service.set_images(db, job_id=job.id, images=[
        DesignJobConfigureImageItem(property_image_id=img.id, input_role="primary"),
    ])
    if with_design_style:
        design_job_service.set_tool_options(db, job_id=job.id, tool_options={"design_style": "Classic"})

    submitted = design_job_service.submit_design_job(db, job_id=job.id)
    return submitted, tool, proj, prop, img


def test_sp001_payload_contract_name(db):
    submitted, *_ = _make_submitted_job(db)
    assert submitted.submitted_payload_json["payload_contract"]["name"] == "aihome.design_job"


def test_sp002_payload_contract_version(db):
    """
    Knowledge Inheritance Engine Phase 1.2A intentionally bumps
    payload_contract.version from "1.0" to "1.1" (approved final
    correction) and adds effective_context_version alongside it - this
    is one of the explicitly-approved cases where new authoritative
    behavior updates a prior expectation, not a regression.
    """
    submitted, *_ = _make_submitted_job(db)
    assert submitted.submitted_payload_json["payload_contract"]["version"] == "1.1"
    assert submitted.submitted_payload_json["payload_contract"]["effective_context_version"] == "1.2.0"
    assert (
        submitted.submitted_payload_json["payload_contract"]["effective_context_version"]
        == submitted.submitted_payload_json["effective_context"]["context_schema_version"]
    )


def test_sp003_business_intent_fields(db):
    submitted, tool, *_ = _make_submitted_job(db)
    bi = submitted.submitted_payload_json["business_intent"]
    assert bi["tool_code"] == tool.tool_code
    assert bi["tool_name"] == tool.tool_name
    assert bi["design_type"] == tool.design_type
    assert bi["business_purpose"] == "Create a redesigned exterior concept."
    assert bi["business_instructions"] == "Preserve the property identity."


def test_sp004_workflow_code_excluded_from_business_sections(db):
    submitted, *_ = _make_submitted_job(db)
    payload = submitted.submitted_payload_json

    assert "workflow_code" not in payload["business_intent"]
    assert "workflow_code" not in payload["request_context"]
    assert "workflow_code" not in payload["effective_context"]
    # But it IS still present at the payload root - kept exactly as the
    # current execution compatibility hint, per inheritance_03 §17.2.
    assert payload["workflow_code"] == "WF_TEST"


def test_sp005_tool_options_present_in_request_context(db):
    submitted, *_ = _make_submitted_job(db)
    assert submitted.submitted_payload_json["request_context"]["tool_options"]["design_style"] == "Classic"


def test_sp006_design_style_promoted_to_request_context(db):
    submitted, *_ = _make_submitted_job(db, with_design_style=True)
    assert submitted.submitted_payload_json["request_context"]["design_style"] == "Classic"


def test_sp007_tool_without_design_style_still_valid(db):
    submitted, *_ = _make_submitted_job(db, with_design_style=False)
    payload = submitted.submitted_payload_json
    assert submitted.status == "submitted"
    assert payload["request_context"]["design_style"] is None


def test_sp008_effective_context_matches_context_builder_output(db):
    submitted, *_ = _make_submitted_job(db)
    assert submitted.submitted_payload_json["effective_context"] == submitted.effective_context_json


def test_sp009_inputs_integrity(db):
    submitted, tool, proj, prop, img = _make_submitted_job(db)
    images = submitted.submitted_payload_json["inputs"]["images"]
    assert len(images) == 1
    assert images[0]["property_image_id"] == img.id


def test_sp010_metadata_trace_fields(db):
    submitted, tool, proj, prop, img = _make_submitted_job(db)
    md = submitted.submitted_payload_json["metadata"]
    assert md["design_job_id"] == submitted.id
    assert md["project_id"] == proj.project_id
    assert md["property_id"] == prop.id
    assert md["tool_id"] == tool.id
    assert md["selected_image_count"] == 1
    assert md["created_from"] == "AI_HOME_DESIGN_STUDIO"


def test_sp011_legacy_top_level_tool_options_alias_still_present(db):
    submitted, *_ = _make_submitted_job(db)
    payload = submitted.submitted_payload_json
    # Legacy top-level key, kept exactly as before Step 5, per
    # inheritance_04 §12.10's explicit compatibility-alias instruction.
    assert "tool_options" in payload
    assert payload["tool_options"]["design_style"] == "Classic"
    assert payload["tool_options"] == payload["request_context"]["tool_options"]


def test_sp012_full_payload_json_serializable(db):
    import json
    submitted, *_ = _make_submitted_job(db)
    serialized = json.dumps(submitted.submitted_payload_json)
    assert isinstance(serialized, str)


def test_legacy_top_level_fields_all_preserved_exactly(db):
    """
    Every field that existed at the payload root BEFORE Step 5 must still
    be there, completely unchanged in shape - this is the core backward
    compatibility guarantee for the one real structural consumer found
    during audit (design_job_execution_service.py reads
    payload['inputs']['images'][*]['url'] directly).
    """
    submitted, tool, proj, prop, img = _make_submitted_job(db)
    payload = submitted.submitted_payload_json

    assert payload["job_number"] == submitted.job_number
    assert payload["tool_code"] == tool.tool_code
    assert payload["design_type"] == tool.design_type
    assert payload["workflow_code"] == tool.workflow_code
    assert payload["project_id"] == proj.project_id
    assert payload["property_id"] == prop.id
    assert "inputs" in payload and "images" in payload["inputs"]
    assert payload["inputs"]["images"][0]["url"] == img.image_url
    assert "tool_options" in payload
    assert "effective_context" in payload

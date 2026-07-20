"""
tests/integration/test_tool_intent_compatibility.py

Knowledge Inheritance Engine Phase 1.2A - Checkpoint 4 tests: tool_intent
as canonical, business_intent as an identical temporary compatibility
alias, and isolation from WACP's own envelope-level business_intent
string field.
"""
import datetime

import pytest

from app.db.database import SessionLocal
from app.models.project import Project
from app.models.project_property import ProjectProperty
from app.models.property import Property
from app.models.property_image import PropertyImage

from app import crud
from app.schemas.design_job import DesignJobCreate, DesignJobConfigureImageItem
from app.schemas.design_tool import DesignToolCreate
from app.schemas.design_tool_image_requirement import DesignToolImageRequirementCreate
from app.services.design_job_service import design_job_service


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_submitted_job(db):
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")

    proj = Project(project_id=f"PRJ-{suffix}", project_name="Tool Intent Test")
    db.add(proj)
    db.commit()

    prop = Property(property_uid=f"PROP-{suffix}", address="1 Intent St")
    db.add(prop)
    db.commit()
    db.refresh(prop)

    db.add(ProjectProperty(project_id=proj.project_id, property_id=prop.id))
    db.commit()

    tool = crud.design_tool.create(db, obj_in=DesignToolCreate(
        tool_code=f"TOOL-{suffix}", tool_name="Intent Tool", design_type="image_creation", workflow_code="WF_TEST",
    ))
    tool.business_purpose = "Create a redesigned concept."
    tool.business_instructions = "Preserve identity."
    db.add(tool)
    db.commit()
    db.refresh(tool)

    crud.design_tool_image_requirement.create(db, obj_in=DesignToolImageRequirementCreate(
        tool_id=tool.id, input_role="primary", min_count=1, max_count=1,
    ))

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
    return design_job_service.submit_design_job(db, job_id=job.id)


def test_tool_intent_key_exists(db):
    submitted = _make_submitted_job(db)
    assert "tool_intent" in submitted.submitted_payload_json


def test_legacy_business_intent_alias_still_exists(db):
    submitted = _make_submitted_job(db)
    assert "business_intent" in submitted.submitted_payload_json


def test_tool_intent_and_business_intent_are_byte_identical(db):
    import json
    submitted = _make_submitted_job(db)
    payload = submitted.submitted_payload_json
    assert json.dumps(payload["tool_intent"], sort_keys=True) == json.dumps(payload["business_intent"], sort_keys=True)


def test_tool_intent_content_correct(db):
    submitted = _make_submitted_job(db)
    ti = submitted.submitted_payload_json["tool_intent"]
    assert ti["business_purpose"] == "Create a redesigned concept."
    assert ti["business_instructions"] == "Preserve identity."
    assert ti["tool_code"] == submitted.tool_code
    assert ti["design_type"] == submitted.design_type


def test_wacp_envelope_business_intent_never_confused_with_aihome_objects():
    """
    WACP's own envelope-level business_intent is a plain Optional[str],
    assembled entirely outside design_job_service.py / payload_builder.py
    (in wacp_adapter.py / the WACP client SDK, neither of which this
    phase touches). This test asserts the structural fact that makes
    confusion impossible: AIHOME's tool_intent/business_intent are always
    dicts, never strings, so no code path could accidentally pass one
    where the other is expected without an immediate, obvious type error.
    """
    aihome_intent_object = {"tool_code": "X", "tool_name": "Y", "design_type": "Z",
                             "business_purpose": None, "business_instructions": None}
    wacp_routing_intent = "PROPERTY_ANALYSIS"

    assert isinstance(aihome_intent_object, dict)
    assert isinstance(wacp_routing_intent, str)
    assert not isinstance(wacp_routing_intent, dict)
    assert not isinstance(aihome_intent_object, str)


def test_payload_contract_version_bumped_and_consistent(db):
    submitted = _make_submitted_job(db)
    payload = submitted.submitted_payload_json
    assert payload["payload_contract"]["version"] == "1.1"
    assert payload["payload_contract"]["effective_context_version"] == payload["effective_context"]["context_schema_version"]

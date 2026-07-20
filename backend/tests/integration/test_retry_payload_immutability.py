"""
tests/integration/test_retry_payload_immutability.py

AI HOME Knowledge Inheritance V1.0 - Step 5 retry/WACP compatibility
coverage, aligned to inheritance_05_validation_test_plan.md §15 (RT-001,
RT-002, RT-003, RT-006) and §17 (WACP-002, WACP-003).
"""
import datetime
import json
from unittest.mock import patch

import pytest

from app.db.database import SessionLocal
from app.models.project import Project
from app.models.project_property import ProjectProperty
from app.models.property import Property
from app.models.property_image import PropertyImage

from app import crud
from app.schemas.workflow_execution import WorkflowExecutionUpdate
from app.schemas.design_job import DesignJobCreate, DesignJobConfigureImageItem
from app.schemas.design_tool import DesignToolCreate
from app.schemas.design_tool_image_requirement import DesignToolImageRequirementCreate
from app.services.design_job_service import design_job_service
from app.services.design_job_execution_service import design_job_execution_service
from app.services import wacp_adapter, payload_builder


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def submitted_job(db):
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")

    proj = Project(project_id=f"PRJ-{suffix}", project_name="Retry Test Project")
    db.add(proj)
    db.commit()

    prop = Property(property_uid=f"PROP-{suffix}", address="1 Retry St")
    db.add(prop)
    db.commit()
    db.refresh(prop)

    db.add(ProjectProperty(project_id=proj.project_id, property_id=prop.id))
    db.commit()

    tool = crud.design_tool.create(db, obj_in=DesignToolCreate(
        tool_code=f"TOOL-{suffix}", tool_name="Retry Tool", design_type="image_creation", workflow_code="WF_RETRY_TEST",
    ))
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
    submitted = design_job_service.submit_design_job(db, job_id=job.id)
    return submitted


def test_rt001_retry_reuses_exact_frozen_payload(db, submitted_job):
    frozen_payload_before = json.dumps(submitted_job.submitted_payload_json, sort_keys=True)

    captured = {}

    def capture_submit(data, *, business_intent=None, workflow_code, project_code, priority="NORMAL", correlation_id=None, callback_url=None):
        captured["data"] = data
        return {"job_id": "DEVTOOLS-INITIAL", "status": "QUEUED"}

    with patch.object(wacp_adapter, "submit_payload", side_effect=capture_submit):
        design_job_execution_service.execute_submitted_job(db, job_id=submitted_job.id)

    # Force the current attempt to Failed so retry is eligible.
    executions, _ = crud.design_job_execution.get_multi(db, design_job_id=submitted_job.id)
    current = [e for e in executions if e.is_current == 1][0]
    wf = crud.workflow_execution.get(db, current.workflow_execution_id)
    crud.workflow_execution.update(db, db_obj=wf, obj_in=WorkflowExecutionUpdate(status="Failed"))

    captured_retry = {}

    def capture_retry(data, *, business_intent=None, workflow_code, project_code, priority="NORMAL", correlation_id=None, callback_url=None):
        captured_retry["data"] = data
        return {"job_id": "DEVTOOLS-RETRY", "status": "QUEUED"}

    with patch.object(wacp_adapter, "submit_payload", side_effect=capture_retry):
        design_job_execution_service.retry_design_job(db, job_id=submitted_job.id)

    # Exact semantic equality between what was sent on execute and on retry.
    assert json.dumps(captured["data"], sort_keys=True) == json.dumps(captured_retry["data"], sort_keys=True)

    # And the stored submitted_payload_json itself was never rewritten.
    db.refresh(submitted_job)
    assert json.dumps(submitted_job.submitted_payload_json, sort_keys=True) == frozen_payload_before


def test_rt002_retry_does_not_call_context_builder(db, submitted_job):
    with patch.object(wacp_adapter, "submit_payload", return_value={"job_id": "X", "status": "QUEUED"}):
        design_job_execution_service.execute_submitted_job(db, job_id=submitted_job.id)

    executions, _ = crud.design_job_execution.get_multi(db, design_job_id=submitted_job.id)
    current = [e for e in executions if e.is_current == 1][0]
    wf = crud.workflow_execution.get(db, current.workflow_execution_id)
    crud.workflow_execution.update(db, db_obj=wf, obj_in=WorkflowExecutionUpdate(status="Failed"))

    with patch.object(payload_builder, "build_design_job_context") as spy_context:
        with patch.object(wacp_adapter, "submit_payload", return_value={"job_id": "Y", "status": "QUEUED"}):
            design_job_execution_service.retry_design_job(db, job_id=submitted_job.id)
        spy_context.assert_not_called()


def test_rt003_retry_does_not_call_input_builder(db, submitted_job):
    with patch.object(wacp_adapter, "submit_payload", return_value={"job_id": "X", "status": "QUEUED"}):
        design_job_execution_service.execute_submitted_job(db, job_id=submitted_job.id)

    executions, _ = crud.design_job_execution.get_multi(db, design_job_id=submitted_job.id)
    current = [e for e in executions if e.is_current == 1][0]
    wf = crud.workflow_execution.get(db, current.workflow_execution_id)
    crud.workflow_execution.update(db, db_obj=wf, obj_in=WorkflowExecutionUpdate(status="Failed"))

    with patch.object(payload_builder, "build_design_job_inputs") as spy_inputs:
        with patch.object(wacp_adapter, "submit_payload", return_value={"job_id": "Y", "status": "QUEUED"}):
            design_job_execution_service.retry_design_job(db, job_id=submitted_job.id)
        spy_inputs.assert_not_called()


def test_rt006_retry_still_supplies_workflow_code_to_wacp(db, submitted_job):
    with patch.object(wacp_adapter, "submit_payload", return_value={"job_id": "X", "status": "QUEUED"}):
        design_job_execution_service.execute_submitted_job(db, job_id=submitted_job.id)

    executions, _ = crud.design_job_execution.get_multi(db, design_job_id=submitted_job.id)
    current = [e for e in executions if e.is_current == 1][0]
    wf = crud.workflow_execution.get(db, current.workflow_execution_id)
    crud.workflow_execution.update(db, db_obj=wf, obj_in=WorkflowExecutionUpdate(status="Failed"))

    captured = {}

    def capture(data, *, business_intent=None, workflow_code, project_code, priority="NORMAL", correlation_id=None, callback_url=None):
        captured["workflow_code"] = workflow_code
        return {"job_id": "Y", "status": "QUEUED"}

    with patch.object(wacp_adapter, "submit_payload", side_effect=capture):
        design_job_execution_service.retry_design_job(db, job_id=submitted_job.id)

    assert captured["workflow_code"] == submitted_job.workflow_code


def test_wacp002_and_wacp003_workflow_code_available_but_isolated_from_business_context(db, submitted_job):
    captured = {}

    def capture(data, *, business_intent=None, workflow_code, project_code, priority="NORMAL", correlation_id=None, callback_url=None):
        captured["workflow_code_param"] = workflow_code
        captured["data"] = data
        return {"job_id": "X", "status": "QUEUED"}

    with patch.object(wacp_adapter, "submit_payload", side_effect=capture):
        design_job_execution_service.execute_submitted_job(db, job_id=submitted_job.id)

    # WACP-002: workflow_code remains available to the adapter/routing path.
    assert captured["workflow_code_param"] == submitted_job.workflow_code

    # WACP-003: workflow_code must not be embedded inside the approved
    # Business Context sections, even though it's still present at the
    # payload root as the transitional compatibility hint.
    assert "workflow_code" not in captured["data"]["business_intent"]
    assert "workflow_code" not in captured["data"]["request_context"]
    assert "workflow_code" not in captured["data"]["effective_context"]

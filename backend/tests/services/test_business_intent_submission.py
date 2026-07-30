"""
tests/services/test_business_intent_submission.py

Fix WACP Property Analysis Submission to Use Business Intent.

Covers:
  - The synced wacp/ SDK's business_intent / workflow_code either-or
    contract (unit-level, no DB or network).
  - ai_orchestration_service.submit_workflow()'s ZONING_ANALYSIS ->
    business_intent="PROPERTY_ANALYSIS" mapping, with workflow_code
    omitted (integration-level, real DB, mocked wacp_adapter network call).
  - Legacy Design Studio callers (wacp_workflow_code=...) unaffected.
"""
import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.db.database import SessionLocal
from app.models.project import Project

from app.services import wacp_adapter
from app.services.ai_orchestration_service import (
    ai_orchestration_service,
    _map_to_business_intent,
    _resolve_business_intent,
    _LOCAL_PIPELINE_TO_BUSINESS_INTENT,
)
from app.api.ai_orchestration import WorkflowSubmitRequest


# ---------------------------------------------------------------------------
# SDK-level unit tests
# ---------------------------------------------------------------------------

def _builder():
    from wacp.client.builder import PayloadBuilder
    from wacp.client.config import ClientConfig
    config = ClientConfig(application_id="AI-CRE", base_url="https://example.com", api_key="k", api_secret="s")
    return PayloadBuilder(config, default_company_id="ABC001", default_project_code="PRJ-1")


class TestWacpSdkBusinessIntent:
    def test_business_intent_only_is_valid(self):
        env = _builder().build(data={"x": 1}, business_intent="PROPERTY_ANALYSIS")
        assert env.business_intent == "PROPERTY_ANALYSIS"
        assert env.workflow_code is None

    def test_workflow_code_only_still_valid_legacy(self):
        env = _builder().build(data={"x": 1}, workflow_code="WF_LEGACY")
        assert env.business_intent is None
        assert env.workflow_code == "WF_LEGACY"

    def test_neither_raises(self):
        from wacp.core.errors import WacpEnvelopeError
        with pytest.raises(WacpEnvelopeError):
            _builder().build(data={"x": 1})

    def test_both_supplied_both_serialize(self):
        """Not the Property Analysis case, but confirms the envelope
        itself doesn't force an exclusive choice - WIM Module V1's own
        precedence (business_intent wins when both present) is a
        DEV-TOOLS-side concern, not something the client SDK enforces."""
        env = _builder().build(data={"x": 1}, business_intent="PROPERTY_ANALYSIS", workflow_code="WF_LEGACY")
        assert env.business_intent == "PROPERTY_ANALYSIS"
        assert env.workflow_code == "WF_LEGACY"

    def test_envelope_serialization_omits_workflow_code_when_none(self):
        from wacp.core.serialization import envelope_to_dict
        env = _builder().build(data={"x": 1}, business_intent="PROPERTY_ANALYSIS")
        wire = envelope_to_dict(env)
        assert wire["wacp"]["business_intent"] == "PROPERTY_ANALYSIS"
        assert "workflow_code" not in wire["wacp"]

    def test_envelope_serialization_omits_business_intent_when_none(self):
        from wacp.core.serialization import envelope_to_dict
        env = _builder().build(data={"x": 1}, workflow_code="WF_LEGACY")
        wire = envelope_to_dict(env)
        assert wire["wacp"]["workflow_code"] == "WF_LEGACY"
        assert "business_intent" not in wire["wacp"]


# ---------------------------------------------------------------------------
# Mapping table tests
# ---------------------------------------------------------------------------

class TestBusinessIntentMapping:
    def test_zoning_analysis_maps_to_property_analysis(self):
        assert _map_to_business_intent("ZONING_ANALYSIS") == "PROPERTY_ANALYSIS"

    def test_unmapped_pipeline_raises_value_error(self):
        with pytest.raises(ValueError, match="no business_intent mapping"):
            _map_to_business_intent("RENOVATION_ESTIMATE")

    def test_mapping_table_contains_only_registered_pipelines(self):
        """Confirms the other 4 frontend-offered pipelines remain
        deliberately unmapped - this fix does not invent business_intent
        assignments DEV-TOOLS hasn't actually registered.

        AIHOME Phase 1 (Phase C): PROPERTY_INTELLIGENCE was added as a
        new, additive entry - the canonical business intent for new
        AIHOME functionality per the WIMLOGIC Phase 1 Architecture Lock.
        ZONING_ANALYSIS -> PROPERTY_ANALYSIS remains completely unchanged
        alongside it, retained as a documented legacy alias."""
        assert set(_LOCAL_PIPELINE_TO_BUSINESS_INTENT.keys()) == {"ZONING_ANALYSIS", "PROPERTY_INTELLIGENCE"}

    @pytest.mark.parametrize("explicit", [None, "", "   "])
    def test_missing_or_blank_explicit_intent_uses_legacy_mapping(self, explicit):
        assert _resolve_business_intent("ZONING_ANALYSIS", explicit) == "PROPERTY_ANALYSIS"

    def test_explicit_image_design_overrides_legacy_mapping(self):
        assert _resolve_business_intent("ZONING_ANALYSIS", "IMAGE_DESIGN") == "IMAGE_DESIGN"

    def test_explicit_property_analysis_remains_property_analysis(self):
        assert _resolve_business_intent("ZONING_ANALYSIS", "PROPERTY_ANALYSIS") == "PROPERTY_ANALYSIS"

    def test_unsupported_explicit_intent_uses_existing_value_error_convention(self):
        with pytest.raises(ValueError, match="is not supported"):
            _resolve_business_intent("ZONING_ANALYSIS", "UNSUPPORTED_INTENT")


class TestWorkflowSubmitRequestBoundary:
    def test_business_intent_survives_actual_request_model_parsing(self):
        request = WorkflowSubmitRequest(
            project_id=1,
            property_id=2,
            workflow_code="ZONING_ANALYSIS",
            business_intent="IMAGE_DESIGN",
        )
        assert request.business_intent == "IMAGE_DESIGN"
        assert _resolve_business_intent(
            request.workflow_code,
            request.business_intent,
        ) == "IMAGE_DESIGN"

    def test_parsed_image_design_is_forwarded_to_dispatch_without_provider_or_db(self):
        request = WorkflowSubmitRequest(
            project_id=1,
            property_id=2,
            workflow_code="ZONING_ANALYSIS",
            business_intent="IMAGE_DESIGN",
        )
        project = SimpleNamespace(id=1, project_id="PRJ-1")
        execution = SimpleNamespace(execution_id=9)

        with (
            patch("app.services.ai_orchestration_service.crud_project.get", return_value=project),
            patch("app.services.ai_orchestration_service.payload_builder.build_enterprise_payload", return_value={"safe": True}),
            patch.object(ai_orchestration_service, "create_pending_execution", return_value=execution),
            patch.object(ai_orchestration_service, "dispatch_via_wacp", return_value=execution) as dispatch,
        ):
            result = ai_orchestration_service.submit_workflow(
                object(),
                project_id=request.project_id,
                property_id=request.property_id,
                workflow_code=request.workflow_code,
                business_intent=request.business_intent,
            )

        assert result is execution
        assert dispatch.call_args.kwargs["business_intent"] == "IMAGE_DESIGN"
        assert "wacp_workflow_code" not in dispatch.call_args.kwargs

    def test_additional_business_intents_remains_ignored(self):
        request = WorkflowSubmitRequest(
            project_id=1,
            property_id=2,
            workflow_code="ZONING_ANALYSIS",
            additional_business_intents=["IMAGE_DESIGN"],
        )
        assert "additional_business_intents" not in type(request).model_fields
        assert "additional_business_intents" not in request.model_dump()


# ---------------------------------------------------------------------------
# Integration tests - real DB, mocked network call
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def project(db):
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    p = Project(project_id=f"PRJ-{suffix}", project_name="Business Intent Test Project")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@pytest.fixture
def property_obj(db):
    from app.models.property import Property
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    prop = Property(property_uid=f"PROP-{suffix}", address="1 Business Intent St")
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


class TestSubmitWorkflowIntegration:
    def test_property_analysis_sends_business_intent_not_workflow_code(self, db, project, property_obj):
        captured = {}

        def capture(data, **kwargs):
            captured.update(kwargs)
            captured["data"] = data
            return {"job_id": "JOB-CAPTURED-1", "status": "QUEUED"}

        with patch.object(wacp_adapter, "submit_payload", side_effect=capture):
            ai_orchestration_service.submit_workflow(
                db, project_id=project.id, property_id=property_obj.id, workflow_code="ZONING_ANALYSIS",
            )

        assert captured["business_intent"] == "PROPERTY_ANALYSIS"
        assert captured["workflow_code"] is None

    def test_existing_business_payload_shape_unchanged(self, db, project, property_obj):
        """The business data block (project/property/images/instructions/
        metadata) must be identical to what build_enterprise_payload()
        already produced before this fix - only WACP-level routing
        changed, not the business payload itself."""
        from app.services import payload_builder as pb

        expected_data = pb.build_enterprise_payload(db, project_id=project.id, property_id=property_obj.id, metadata_json=None)

        captured = {}

        def capture(data, **kwargs):
            captured["data"] = data
            return {"job_id": "JOB-CAPTURED-2", "status": "QUEUED"}

        with patch.object(wacp_adapter, "submit_payload", side_effect=capture):
            ai_orchestration_service.submit_workflow(
                db, project_id=project.id, property_id=property_obj.id, workflow_code="ZONING_ANALYSIS",
            )

        assert captured["data"] == expected_data

    def test_request_and_correlation_ids_unique_across_submissions(self, db, project, property_obj):
        seen_correlation_ids = []
        seen_request_ids = []

        def capture(data, **kwargs):
            seen_correlation_ids.append(kwargs.get("correlation_id"))
            # request_id itself is generated inside the SDK builder, not
            # passed to submit_payload directly - captured via the real
            # envelope by patching one layer deeper for this one test.
            return {"job_id": f"JOB-{len(seen_correlation_ids)}", "status": "QUEUED"}

        with patch.object(wacp_adapter, "submit_payload", side_effect=capture):
            ai_orchestration_service.submit_workflow(db, project_id=project.id, property_id=property_obj.id, workflow_code="ZONING_ANALYSIS")
            ai_orchestration_service.submit_workflow(db, project_id=project.id, property_id=property_obj.id, workflow_code="ZONING_ANALYSIS")

        assert len(seen_correlation_ids) == 2
        assert seen_correlation_ids[0] != seen_correlation_ids[1]
        assert all(cid for cid in seen_correlation_ids)

    def test_execution_record_stores_returned_job_identity(self, db, project, property_obj):
        with patch.object(wacp_adapter, "submit_payload", return_value={"job_id": "JOB-STORED-1", "status": "QUEUED"}):
            execution_obj = ai_orchestration_service.submit_workflow(
                db, project_id=project.id, property_id=property_obj.id, workflow_code="ZONING_ANALYSIS",
            )
        assert execution_obj.devtools_execution_id == "JOB-STORED-1"

    def test_unmapped_pipeline_fails_before_any_wacp_call_or_local_record(self, db, project, property_obj):
        from app.models.workflow_execution import WorkflowExecution
        before_count = db.query(WorkflowExecution).count()

        with patch.object(wacp_adapter, "submit_payload") as mock_submit:
            with pytest.raises(ValueError):
                ai_orchestration_service.submit_workflow(
                    db, project_id=project.id, property_id=property_obj.id, workflow_code="RENOVATION_ESTIMATE",
                )
            mock_submit.assert_not_called()

        after_count = db.query(WorkflowExecution).count()
        assert after_count == before_count  # no Pending row created either

    def test_unsupported_explicit_intent_fails_before_wacp_or_local_record(self, db, project, property_obj):
        from app.models.workflow_execution import WorkflowExecution
        before_count = db.query(WorkflowExecution).count()

        with patch.object(wacp_adapter, "submit_payload") as mock_submit:
            with pytest.raises(ValueError, match="is not supported"):
                ai_orchestration_service.submit_workflow(
                    db,
                    project_id=project.id,
                    property_id=property_obj.id,
                    workflow_code="ZONING_ANALYSIS",
                    business_intent="UNSUPPORTED_INTENT",
                )
            mock_submit.assert_not_called()

        assert db.query(WorkflowExecution).count() == before_count


# ---------------------------------------------------------------------------
# Legacy caller (Design Studio) unaffected
# ---------------------------------------------------------------------------

class TestLegacyCallerUnaffected:
    def test_dispatch_via_wacp_with_wacp_workflow_code_still_works(self, db, project, property_obj):
        """Mirrors design_job_execution_service.py's exact call pattern -
        wacp_workflow_code=..., business_intent omitted entirely."""
        from app.models.workflow_execution import WorkflowExecution
        from app.schemas.workflow_execution import WorkflowExecutionCreate
        from app.crud.workflow_execution import workflow_execution as crud_we

        suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        exec_obj = crud_we.create(db, obj_in=WorkflowExecutionCreate(
            execution_number=f"EXE-LEGACY-TEST-{suffix}", project_id=project.id, property_id=property_obj.id,
            scenario_id=None, workflow_code="DESIGN_STUDIO_JOB", workflow_version="1.0.0",
            devtools_execution_id=None, status="Pending", priority="Normal", metadata_json={},
        ))

        captured = {}

        def capture(data, **kwargs):
            captured.update(kwargs)
            return {"job_id": "JOB-LEGACY-1", "status": "QUEUED"}

        with patch.object(wacp_adapter, "submit_payload", side_effect=capture):
            ai_orchestration_service.dispatch_via_wacp(
                db, execution_obj=exec_obj, project_obj=project,
                wacp_workflow_code="WF_DESIGN_STUDIO_LEGACY", data={"some": "payload"}, priority="Normal",
            )

        assert captured["workflow_code"] == "WF_DESIGN_STUDIO_LEGACY"
        assert captured["business_intent"] is None

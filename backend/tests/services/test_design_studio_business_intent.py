"""
tests/services/test_design_studio_business_intent.py

AIHOME RC2 / WIM Module V2 - confirms Design Studio's WACP dispatch
submits business_intent="IMAGE_DESIGN_ONLY" instead of either the
Phase 1 DESIGN_STUDIO intent or the legacy
wacp_workflow_code=job.workflow_code - and that Property Analysis/Property
Intelligence's own submission paths remain completely unaffected by
this change (they live in a different file, ai_orchestration_service.py,
touched only for the new additive PROPERTY_INTELLIGENCE mapping entry).
"""
from unittest.mock import patch

import pytest

from app.services import wacp_adapter
from app.services.design_job_execution_service import design_job_execution_service
from app.services.ai_orchestration_service import _map_to_business_intent, _LOCAL_PIPELINE_TO_BUSINESS_INTENT

from tests.integration.test_submitted_payload_contract import _make_submitted_job


@pytest.fixture
def db():
    from app.db.database import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestDesignStudioSubmitsBusinessIntent:
    def test_execute_submitted_job_sends_business_intent_image_design_only(self, db):
        submitted, tool, proj, prop, img = _make_submitted_job(db)

        captured = {}

        def capture(data, **kwargs):
            captured.update(kwargs)
            return {"job_id": "JOB-DESIGN-STUDIO-TEST", "status": "QUEUED"}

        with patch.object(wacp_adapter, "submit_payload", side_effect=capture):
            design_job_execution_service.execute_submitted_job(db, job_id=submitted.id)

        assert captured["business_intent"] == "IMAGE_DESIGN_ONLY"

    def test_execute_submitted_job_no_longer_sends_workflow_code(self, db):
        """The legacy field must be genuinely absent (None), not just
        unused - confirming AIHOME does not encode a workflow_code
        alongside business_intent for this call site."""
        submitted, tool, proj, prop, img = _make_submitted_job(db)

        captured = {}

        def capture(data, **kwargs):
            captured.update(kwargs)
            return {"job_id": "JOB-DESIGN-STUDIO-TEST-2", "status": "QUEUED"}

        with patch.object(wacp_adapter, "submit_payload", side_effect=capture):
            design_job_execution_service.execute_submitted_job(db, job_id=submitted.id)

        assert captured["workflow_code"] is None


class TestPropertyIntelligenceMapping:
    def test_property_intelligence_is_a_new_additive_entry(self):
        assert _map_to_business_intent("PROPERTY_INTELLIGENCE") == "PROPERTY_INTELLIGENCE"

    def test_legacy_zoning_analysis_mapping_completely_unchanged(self):
        """The exact backward-compatibility guarantee this phase is bound
        by - existing callers of the legacy pipeline code must keep
        receiving exactly the business_intent they always have."""
        assert _map_to_business_intent("ZONING_ANALYSIS") == "PROPERTY_ANALYSIS"

    def test_both_entries_coexist_neither_overwrites_the_other(self):
        assert _LOCAL_PIPELINE_TO_BUSINESS_INTENT == {
            "ZONING_ANALYSIS": "PROPERTY_ANALYSIS",
            "PROPERTY_INTELLIGENCE": "PROPERTY_INTELLIGENCE",
        }

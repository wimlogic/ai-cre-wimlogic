"""
tests/services/test_payload_builder.py

AI HOME Knowledge Inheritance V1.0 - Step 3 test coverage for
payload_builder._build_property_ai_analysis(), per
inheritance_04_backend_implementation.md §20.2 "Normalizer Tests".

These are true in-memory unit tests, not integration tests - the function
under test only reads column attributes off an ORM instance (never
touches relationships, never queries the database), so a plain
PropertyAnalysisReport() constructed directly in Python is sufficient;
no database connection, session, or fixture is required here.
"""
import datetime
import json
from decimal import Decimal

from app.models.property_analysis_report import PropertyAnalysisReport
from app.services.payload_builder import _build_property_ai_analysis


def _make_report(**overrides) -> PropertyAnalysisReport:
    defaults = dict(
        id=42,
        project_id="PRJ-7328",
        property_id=927,
        workflow_execution_id=101,
        workflow_result_id=202,
        analysis_version="1.0",
        workflow_status="Completed",
        completed_at=datetime.datetime(2026, 7, 17, 0, 0, 0),
        recommendation="Proceed with cosmetic exterior improvements.",
        score=Decimal("82.00"),
        confidence_score=Decimal("0.91"),
        zoning_notes="Existing use appears compatible.",
        risk_notes="Verify setback requirements before structural expansion.",
        estimate_low=Decimal("25000.00"),
        estimate_high=Decimal("42000.00"),
        report_json={"raw": "extended output that must never leak"},
    )
    defaults.update(overrides)
    return PropertyAnalysisReport(**defaults)


def test_maps_all_named_structured_fields():
    report = _make_report()
    result = _build_property_ai_analysis(report)

    assert result["analysis_report_id"] == 42
    assert result["workflow_execution_id"] == 101
    assert result["workflow_result_id"] == 202
    assert result["analysis_version"] == "1.0"
    assert result["status"] == "Completed"
    assert result["summary"]["recommendation"] == "Proceed with cosmetic exterior improvements."
    assert result["summary"]["score"] == 82.0
    assert result["summary"]["confidence_score"] == 0.91
    assert result["findings"]["zoning_notes"] == "Existing use appears compatible."
    assert result["findings"]["risk_notes"] == "Verify setback requirements before structural expansion."
    assert result["estimate"]["low"] == 25000.0
    assert result["estimate"]["high"] == 42000.0
    assert result["source_reference"]["report_id"] == 42


def test_decimal_fields_convert_to_json_safe_numeric():
    report = _make_report(score=Decimal("82.50"), confidence_score=Decimal("0.9123"),
                           estimate_low=Decimal("25000.00"), estimate_high=Decimal("42000.75"))
    result = _build_property_ai_analysis(report)

    assert isinstance(result["summary"]["score"], float)
    assert result["summary"]["score"] == 82.5
    assert isinstance(result["summary"]["confidence_score"], float)
    assert isinstance(result["estimate"]["low"], float)
    assert isinstance(result["estimate"]["high"], float)
    assert result["estimate"]["high"] == 42000.75


def test_datetime_converts_to_normalized_iso_string():
    report = _make_report(completed_at=datetime.datetime(2026, 7, 17, 9, 30, 15))
    result = _build_property_ai_analysis(report)

    assert isinstance(result["completed_at"], str)
    assert result["completed_at"] == datetime.datetime(2026, 7, 17, 9, 30, 15).isoformat()


def test_null_values_preserved_safely():
    report = _make_report(
        workflow_execution_id=None,
        workflow_result_id=None,
        analysis_version=None,
        completed_at=None,
        recommendation=None,
        score=None,
        confidence_score=None,
        zoning_notes=None,
        risk_notes=None,
        estimate_low=None,
        estimate_high=None,
    )
    result = _build_property_ai_analysis(report)

    assert result["workflow_execution_id"] is None
    assert result["workflow_result_id"] is None
    assert result["analysis_version"] is None
    assert result["completed_at"] is None
    assert result["summary"]["recommendation"] is None
    assert result["summary"]["score"] is None
    assert result["summary"]["confidence_score"] is None
    assert result["findings"]["zoning_notes"] is None
    assert result["findings"]["risk_notes"] is None
    assert result["estimate"]["low"] is None
    assert result["estimate"]["high"] is None
    # id and status are non-nullable columns on the real schema, so they
    # are not exercised as null cases here - only genuinely nullable
    # fields are tested null.


def test_result_is_directly_json_serializable():
    report = _make_report()
    result = _build_property_ai_analysis(report)
    # Must not raise - proves every value is already JSON-safe with no
    # custom encoder required downstream, consistent with how the rest
    # of this codebase's frozen payloads are serialized.
    serialized = json.dumps(result)
    assert isinstance(serialized, str)


def test_excludes_report_json():
    report = _make_report(report_json={"secret_extended_data": "must never appear in effective context"})
    result = _build_property_ai_analysis(report)

    assert "report_json" not in result
    assert "raw_api_json" not in result
    # Also confirm nothing about report_json's actual content leaked into
    # any nested block by accident.
    serialized = json.dumps(result)
    assert "secret_extended_data" not in serialized
    assert "must never appear" not in serialized


def test_does_not_leak_orm_relationship_or_internal_state():
    report = _make_report()
    result = _build_property_ai_analysis(report)

    assert "_sa_instance_state" not in result
    assert "project" not in result
    assert "property" not in result
    assert "scenario" not in result
    assert "workflow_execution" not in result
    assert "workflow_result" not in result
    # Exactly the five documented top-level keys, nothing more.
    assert set(result.keys()) == {
        "analysis_report_id", "workflow_execution_id", "workflow_result_id",
        "analysis_version", "status", "completed_at", "summary", "findings",
        "estimate", "source_reference",
    }


def test_does_not_mutate_source_orm_object():
    report = _make_report()
    original_recommendation = report.recommendation
    original_score = report.score

    _build_property_ai_analysis(report)

    assert report.recommendation == original_recommendation
    assert report.score == original_score
    assert isinstance(report.score, Decimal)  # unchanged in place - still the original Decimal, not the normalized float

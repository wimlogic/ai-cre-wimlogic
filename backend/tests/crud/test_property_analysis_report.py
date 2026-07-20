"""
tests/crud/test_property_analysis_report.py

AI HOME Knowledge Inheritance V1.0 - Step 2 test coverage for
CRUDPropertyAnalysisReport.get_latest_completed_for_project_property(),
per inheritance_04_backend_implementation.md §20.1 "Property Analysis
Resolver Tests" (all 8 required scenarios).

Runs against a real database connection (this repository has no existing
mocking/fixture framework or conftest.py to reuse - consistent with how
every other backend checkpoint in this project has been validated, these
tests use the real SessionLocal against the configured MySQL/MariaDB
instance rather than inventing a new, competing test-doubles convention).
"""
import datetime

import pytest

from app.db.database import SessionLocal
from app.models.project import Project
from app.models.property import Property
from app.models.property_analysis_report import PropertyAnalysisReport
from app.crud.property_analysis_report import property_analysis_report as crud_par


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seed(db):
    """One project pair and three properties, isolated by a random suffix
    so this test file can run repeatedly without colliding with any other
    data already in the shared test database."""
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")

    proj_a = Project(project_id=f"PRJ-A-{suffix}", project_name="Project A")
    proj_b = Project(project_id=f"PRJ-B-{suffix}", project_name="Project B")
    db.add_all([proj_a, proj_b])
    db.commit()

    prop_a = Property(property_uid=f"PROP-A-{suffix}", address="1 A St")
    prop_b = Property(property_uid=f"PROP-B-{suffix}", address="2 B St")
    prop_c = Property(property_uid=f"PROP-C-{suffix}", address="3 C St")
    db.add_all([prop_a, prop_b, prop_c])
    db.commit()
    db.refresh(prop_a)
    db.refresh(prop_b)
    db.refresh(prop_c)

    return {"proj_a": proj_a, "proj_b": proj_b, "prop_a": prop_a, "prop_b": prop_b, "prop_c": prop_c}


def _report(db, *, project_id, property_id, workflow_status, completed_at, recommendation):
    r = PropertyAnalysisReport(
        project_id=project_id,
        property_id=property_id,
        workflow_status=workflow_status,
        completed_at=completed_at,
        recommendation=recommendation,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def test_returns_latest_completed_report_for_exact_pair(db, seed):
    _report(db, project_id=seed["proj_a"].project_id, property_id=seed["prop_a"].id,
             workflow_status="Completed", completed_at=datetime.datetime(2026, 1, 1), recommendation="old")
    _report(db, project_id=seed["proj_a"].project_id, property_id=seed["prop_a"].id,
             workflow_status="Completed", completed_at=datetime.datetime(2026, 6, 1), recommendation="newest")

    got = crud_par.get_latest_completed_for_project_property(
        db, project_id=seed["proj_a"].project_id, property_id=seed["prop_a"].id
    )
    assert got is not None
    assert got.recommendation == "newest"


def test_orders_by_completed_at_desc_then_id_desc_tiebreak(db, seed):
    same_ts = datetime.datetime(2026, 6, 1)
    _report(db, project_id=seed["proj_a"].project_id, property_id=seed["prop_a"].id,
             workflow_status="Completed", completed_at=same_ts, recommendation="first_at_this_timestamp")
    later = _report(db, project_id=seed["proj_a"].project_id, property_id=seed["prop_a"].id,
                     workflow_status="Completed", completed_at=same_ts, recommendation="second_at_this_timestamp")

    got = crud_par.get_latest_completed_for_project_property(
        db, project_id=seed["proj_a"].project_id, property_id=seed["prop_a"].id
    )
    assert got is not None
    assert got.id == later.id


def test_ignores_reports_for_another_project(db, seed):
    _report(db, project_id=seed["proj_a"].project_id, property_id=seed["prop_a"].id,
             workflow_status="Completed", completed_at=datetime.datetime(2026, 1, 1), recommendation="correct_project")
    _report(db, project_id=seed["proj_b"].project_id, property_id=seed["prop_a"].id,
             workflow_status="Completed", completed_at=datetime.datetime(2027, 1, 1), recommendation="wrong_project_later_date")

    got = crud_par.get_latest_completed_for_project_property(
        db, project_id=seed["proj_a"].project_id, property_id=seed["prop_a"].id
    )
    assert got is not None
    assert got.recommendation == "correct_project"


def test_ignores_reports_for_another_property(db, seed):
    _report(db, project_id=seed["proj_a"].project_id, property_id=seed["prop_a"].id,
             workflow_status="Completed", completed_at=datetime.datetime(2026, 1, 1), recommendation="correct_property")
    _report(db, project_id=seed["proj_a"].project_id, property_id=seed["prop_b"].id,
             workflow_status="Completed", completed_at=datetime.datetime(2027, 1, 1), recommendation="wrong_property_later_date")

    got = crud_par.get_latest_completed_for_project_property(
        db, project_id=seed["proj_a"].project_id, property_id=seed["prop_a"].id
    )
    assert got is not None
    assert got.recommendation == "correct_property"


def test_ignores_incomplete_reports(db, seed):
    _report(db, project_id=seed["proj_a"].project_id, property_id=seed["prop_a"].id,
             workflow_status="Completed", completed_at=datetime.datetime(2026, 1, 1), recommendation="eligible")
    _report(db, project_id=seed["proj_a"].project_id, property_id=seed["prop_a"].id,
             workflow_status="Pending", completed_at=datetime.datetime(2028, 1, 1), recommendation="pending_status_later_date")
    _report(db, project_id=seed["proj_a"].project_id, property_id=seed["prop_a"].id,
             workflow_status="Completed", completed_at=None, recommendation="null_completed_at")

    got = crud_par.get_latest_completed_for_project_property(
        db, project_id=seed["proj_a"].project_id, property_id=seed["prop_a"].id
    )
    assert got is not None
    assert got.recommendation == "eligible"


def test_returns_none_when_no_eligible_report_exists(db, seed):
    got = crud_par.get_latest_completed_for_project_property(
        db, project_id=seed["proj_a"].project_id, property_id=seed["prop_c"].id
    )
    assert got is None


def test_does_not_expose_raw_api_json(db, seed):
    """
    raw_api_json lives on cre_properties, not cre_property_analysis_reports -
    the model has no such column at all, confirming there is no code path by
    which this resolver could ever surface it.
    """
    assert not hasattr(PropertyAnalysisReport, "raw_api_json")


def test_never_uses_unordered_first(db, seed):
    """
    Regression guard: ties MUST resolve via id DESC, never via whatever
    order the database happens to return rows in. Seeds 5 reports with the
    identical completed_at and asserts the highest id always wins,
    repeated across a few calls to reduce the odds of a false pass from
    incidental physical row order.
    """
    same_ts = datetime.datetime(2026, 3, 1)
    last = None
    for i in range(5):
        last = _report(db, project_id=seed["proj_a"].project_id, property_id=seed["prop_a"].id,
                        workflow_status="Completed", completed_at=same_ts, recommendation=f"row_{i}")

    for _ in range(3):
        got = crud_par.get_latest_completed_for_project_property(
            db, project_id=seed["proj_a"].project_id, property_id=seed["prop_a"].id
        )
        assert got.id == last.id

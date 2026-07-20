"""
tests/services/test_knowledge_context_builder.py

Knowledge Inheritance Engine Phase 1.2A - Checkpoint 2 unit tests for
knowledge_context_builder.py. Pure unit tests - no database needed, since
the module itself performs no DB access (a plain object with the right
attributes is sufficient).
"""
from types import SimpleNamespace

from app.services.knowledge_context_builder import (
    LEGACY_SCOPE_FIELDS,
    FIELD_RULE_REGISTRY,
    build_project_knowledge_fields,
    build_property_knowledge_fields,
    build_image_knowledge_fields,
    build_design_job_knowledge_fields,
)


def _rule(field_code, scope="project"):
    return SimpleNamespace(field_code=field_code, knowledge_scope=scope)


# ---------------------------------------------------------------------------
# Registry shape
# ---------------------------------------------------------------------------

def test_legacy_scope_fields_has_all_four_scopes():
    assert set(LEGACY_SCOPE_FIELDS.keys()) == {"project", "property", "image", "design_job"}


def test_legacy_scope_fields_design_job_is_empty():
    assert LEGACY_SCOPE_FIELDS["design_job"] == []


def test_legacy_scope_fields_matches_current_shipped_behavior():
    assert LEGACY_SCOPE_FIELDS["project"] == ["project_id", "project_name", "description"]
    assert LEGACY_SCOPE_FIELDS["property"] == [
        "address", "city", "state", "zip", "apn", "zoning_code", "existing_use", "notes", "ai_analysis",
    ]
    assert LEGACY_SCOPE_FIELDS["image"] == [
        "image_role", "notes", "ai_prompt", "tags", "constraints", "priority", "is_primary", "status",
    ]


def test_field_rule_registry_has_16_entries():
    assert len(FIELD_RULE_REGISTRY) == 16


def test_every_registry_entry_scope_is_valid():
    for code, entry in FIELD_RULE_REGISTRY.items():
        assert entry["scope"] in ("project", "property", "image", "design_job")
        assert code.startswith(entry["scope"].upper())  # e.g. PROJECT.*, DESIGN_JOB.*


# ---------------------------------------------------------------------------
# Per-field collection - each of the 16 fields individually
# ---------------------------------------------------------------------------

def test_project_goals_collected_when_granted():
    project_obj = SimpleNamespace(goals="Maximize resale value.")
    result = build_project_knowledge_fields(project_obj, [_rule("PROJECT.GOALS")])
    assert result == {"goals": "Maximize resale value."}


def test_project_budget_composite_field():
    project_obj = SimpleNamespace(budget_low=50000.0, budget_high=80000.0)
    result = build_project_knowledge_fields(project_obj, [_rule("PROJECT.BUDGET")])
    assert result == {"budget": {"low": 50000.0, "high": 80000.0}}


def test_project_preferred_styles():
    project_obj = SimpleNamespace(preferred_styles=["Modern", "Craftsman"])
    result = build_project_knowledge_fields(project_obj, [_rule("PROJECT.PREFERRED_STYLES")])
    assert result == {"preferred_styles": ["Modern", "Craftsman"]}


def test_project_design_preferences():
    project_obj = SimpleNamespace(design_preferences="Avoid stucco.")
    result = build_project_knowledge_fields(project_obj, [_rule("PROJECT.DESIGN_PREFERENCES")])
    assert result == {"design_preferences": "Avoid stucco."}


def test_project_hoa_rules():
    project_obj = SimpleNamespace(hoa_rules="Roof color restricted.")
    result = build_project_knowledge_fields(project_obj, [_rule("PROJECT.HOA_RULES")])
    assert result == {"hoa_rules": "Roof color restricted."}


def test_project_climate():
    project_obj = SimpleNamespace(climate="Semi-arid.")
    result = build_project_knowledge_fields(project_obj, [_rule("PROJECT.CLIMATE")])
    assert result == {"climate": "Semi-arid."}


def test_property_bedrooms():
    property_obj = SimpleNamespace(bedrooms=3)
    result = build_property_knowledge_fields(property_obj, [_rule("PROPERTY.BEDROOMS", "property")])
    assert result == {"bedrooms": 3}


def test_property_bathrooms():
    property_obj = SimpleNamespace(bathrooms=2.5)
    result = build_property_knowledge_fields(property_obj, [_rule("PROPERTY.BATHROOMS", "property")])
    assert result == {"bathrooms": 2.5}


def test_property_construction_type():
    property_obj = SimpleNamespace(construction_type="Wood frame")
    result = build_property_knowledge_fields(property_obj, [_rule("PROPERTY.CONSTRUCTION_TYPE", "property")])
    assert result == {"construction_type": "Wood frame"}


def test_property_existing_materials():
    property_obj = SimpleNamespace(existing_materials=["shingle siding"])
    result = build_property_knowledge_fields(property_obj, [_rule("PROPERTY.EXISTING_MATERIALS", "property")])
    assert result == {"existing_materials": ["shingle siding"]}


def test_property_existing_colors():
    property_obj = SimpleNamespace(existing_colors=["cream"])
    result = build_property_knowledge_fields(property_obj, [_rule("PROPERTY.EXISTING_COLORS", "property")])
    assert result == {"existing_colors": ["cream"]}


def test_image_camera_direction():
    image_obj = SimpleNamespace(camera_direction="north")
    result = build_image_knowledge_fields(image_obj, [_rule("IMAGE.CAMERA_DIRECTION", "image")])
    assert result == {"camera_direction": "north"}


def test_image_existing_furniture():
    image_obj = SimpleNamespace(existing_furniture=["sofa"])
    result = build_image_knowledge_fields(image_obj, [_rule("IMAGE.EXISTING_FURNITURE", "image")])
    assert result == {"existing_furniture": ["sofa"]}


def test_image_existing_lighting():
    image_obj = SimpleNamespace(existing_lighting="natural daylight")
    result = build_image_knowledge_fields(image_obj, [_rule("IMAGE.EXISTING_LIGHTING", "image")])
    assert result == {"existing_lighting": "natural daylight"}


def test_design_job_prompt():
    job_obj = SimpleNamespace(job_prompt="Modernize the exterior.")
    result = build_design_job_knowledge_fields(job_obj, [_rule("DESIGN_JOB.PROMPT", "design_job")])
    assert result == {"job_prompt": "Modernize the exterior."}


def test_design_job_constraints():
    job_obj = SimpleNamespace(job_constraints="Stay within budget.")
    result = build_design_job_knowledge_fields(job_obj, [_rule("DESIGN_JOB.CONSTRAINTS", "design_job")])
    assert result == {"job_constraints": "Stay within budget."}


# ---------------------------------------------------------------------------
# No leakage across fields/scopes
# ---------------------------------------------------------------------------

def test_only_granted_field_appears_not_others():
    project_obj = SimpleNamespace(goals="G", budget_low=1, budget_high=2, preferred_styles=["x"])
    result = build_project_knowledge_fields(project_obj, [_rule("PROJECT.GOALS")])
    assert result == {"goals": "G"}
    assert "budget" not in result
    assert "preferred_styles" not in result


def test_no_field_code_rows_produce_empty_result():
    """The blanket (field_code=NULL) row is not this module's concern -
    it must produce zero effect here, confirming LEGACY_SCOPE_FIELDS
    handling stays entirely separate from this collector."""
    project_obj = SimpleNamespace(project_id="X", project_name="Y", description="Z")
    result = build_project_knowledge_fields(project_obj, [_rule(None)])
    assert result == {}


def test_new_orm_attribute_with_no_rule_produces_no_change():
    """Core acceptance guarantee: a live object can have ANY attribute
    populated - if there's no rule granting it, it never appears."""
    project_obj = SimpleNamespace(goals="Should not appear", hoa_rules="Should not appear either")
    result = build_project_knowledge_fields(project_obj, [])
    assert result == {}


# ---------------------------------------------------------------------------
# Unknown / mismatched field_code policy
# ---------------------------------------------------------------------------

def test_unknown_field_code_excluded_not_raised(caplog):
    project_obj = SimpleNamespace(goals="G")
    result = build_project_knowledge_fields(project_obj, [_rule("PROJECT.NOT_A_REAL_CODE")])
    assert result == {}
    assert "unrecognized field_code" in caplog.text.lower() or "unrecognized" in caplog.text.lower()


def test_scope_mismatch_excluded_not_raised(caplog):
    """A rule row claims knowledge_scope='project' but the field_code is
    actually registered for 'image' - excluded, logged, never raised."""
    project_obj = SimpleNamespace(camera_direction="north")
    result = build_project_knowledge_fields(project_obj, [_rule("IMAGE.CAMERA_DIRECTION", scope="project")])
    assert result == {}


def test_unknown_code_does_not_prevent_other_valid_rules_in_same_call():
    project_obj = SimpleNamespace(goals="G", bogus_field="ignored")
    result = build_project_knowledge_fields(
        project_obj, [_rule("PROJECT.NOT_A_REAL_CODE"), _rule("PROJECT.GOALS")]
    )
    assert result == {"goals": "G"}

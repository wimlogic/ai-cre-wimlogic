"""
app/services/knowledge_context_builder.py

AI HOME Knowledge Inheritance Engine - Phase 1.2A.

This module is a pure COLLECTOR, not a resolver. Phase 1.2 contains
context AGGREGATION only - every field here belongs to exactly one
hierarchy level and is simply gathered into effective_context. There is
deliberately no resolve_inherited_field() or any universal Image ->
Property -> Project override chain: no field in this phase is genuinely
supported at more than one level with child-overrides-parent precedence
(see the approved architecture's field ownership matrix). If a future
field is ever added at two levels with a deliberate override
relationship, that needs its own explicit design at that time.

No database access happens in this module - every function here is a
pure, synchronous transform over already-loaded ORM objects, independently
unit-testable without a session.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LEGACY_SCOPE_FIELDS
# ---------------------------------------------------------------------------
# Exactly the fields a blanket (field_code IS NULL) Knowledge Rule already
# produces today, verbatim from the current, already-shipped
# build_design_job_context() - confirmed against actual source, not
# memory (app/services/payload_builder.py, pre-Phase-1.2A). This list is
# FROZEN as of Phase 1.2A; it must never be edited to "catch up" with new
# ORM columns. A blanket rule's output is defined by this list alone, not
# by introspecting the model - this is the hard guarantee that existing
# Tools' frozen payload shape cannot silently change.
LEGACY_SCOPE_FIELDS: Dict[str, List[str]] = {
    "project": [
        "project_id",
        "project_name",
        "description",
    ],
    "property": [
        "address",
        "city",
        "state",
        "zip",
        "apn",
        "zoning_code",
        "existing_use",
        "notes",
        "ai_analysis",  # already shipped in Knowledge Inheritance V1.0, not new to 1.2
    ],
    "image": [
        "image_role",
        "notes",
        "ai_prompt",
        "tags",
        "constraints",
        "priority",
        "is_primary",
        "status",
    ],
    "design_job": [
        # design_job did not exist as a Knowledge Rule scope before Phase
        # 1.2 - there is no legacy behavior to preserve here. A blanket
        # design_job-scope rule (if one is ever created) produces
        # nothing; every design_job field requires its own explicit
        # FIELD_RULE_REGISTRY entry, with no exception.
    ],
}


# ---------------------------------------------------------------------------
# FIELD_RULE_REGISTRY
# ---------------------------------------------------------------------------
# The sole source of truth for which new (Phase 1.2A) fields a Tool may be
# explicitly granted, one entry per namespaced field_code. "attributes" is
# always a list (even when it names only one ORM attribute) so a single
# shape covers PROJECT.BUDGET's two-column composite without a special
# case elsewhere in this module.
FIELD_RULE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "PROJECT.GOALS":              {"scope": "project",    "attributes": ["goals"],                     "context_key": "goals"},
    "PROJECT.BUDGET":             {"scope": "project",    "attributes": ["budget_low", "budget_high"],  "context_key": "budget"},
    "PROJECT.PREFERRED_STYLES":   {"scope": "project",    "attributes": ["preferred_styles"],           "context_key": "preferred_styles"},
    "PROJECT.DESIGN_PREFERENCES": {"scope": "project",    "attributes": ["design_preferences"],         "context_key": "design_preferences"},
    "PROJECT.HOA_RULES":          {"scope": "project",    "attributes": ["hoa_rules"],                  "context_key": "hoa_rules"},
    "PROJECT.CLIMATE":            {"scope": "project",    "attributes": ["climate"],                    "context_key": "climate"},

    "PROPERTY.BEDROOMS":           {"scope": "property",  "attributes": ["bedrooms"],                   "context_key": "bedrooms"},
    "PROPERTY.BATHROOMS":          {"scope": "property",  "attributes": ["bathrooms"],                  "context_key": "bathrooms"},
    "PROPERTY.CONSTRUCTION_TYPE":  {"scope": "property",  "attributes": ["construction_type"],          "context_key": "construction_type"},
    "PROPERTY.EXISTING_MATERIALS": {"scope": "property",  "attributes": ["existing_materials"],         "context_key": "existing_materials"},
    "PROPERTY.EXISTING_COLORS":    {"scope": "property",  "attributes": ["existing_colors"],             "context_key": "existing_colors"},

    "IMAGE.CAMERA_DIRECTION":      {"scope": "image",      "attributes": ["camera_direction"],           "context_key": "camera_direction"},
    "IMAGE.EXISTING_FURNITURE":    {"scope": "image",      "attributes": ["existing_furniture"],         "context_key": "existing_furniture"},
    "IMAGE.EXISTING_LIGHTING":     {"scope": "image",      "attributes": ["existing_lighting"],          "context_key": "existing_lighting"},

    "DESIGN_JOB.PROMPT":           {"scope": "design_job", "attributes": ["job_prompt"],                 "context_key": "job_prompt"},
    "DESIGN_JOB.CONSTRAINTS":      {"scope": "design_job", "attributes": ["job_constraints"],            "context_key": "job_constraints"},
}


def _resolve_field_rule(field_code: str, expected_scope: str) -> Optional[Dict[str, Any]]:
    """
    Looks up field_code in FIELD_RULE_REGISTRY and validates its scope
    matches expected_scope (the Knowledge Rule row's own knowledge_scope).

    Returns None - never raises - for both an unrecognized code and a
    scope/prefix mismatch. Both cases are logged as warnings and treated
    identically: "this rule row doesn't correspond to a valid, recognized
    grant," excluded from context assembly. This is a deliberate,
    approved policy choice (fail toward exclusion, never toward
    unexpected inclusion or a submission-blocking error over a
    configuration-data issue).
    """
    entry = FIELD_RULE_REGISTRY.get(field_code)
    if entry is None:
        logger.warning(
            "knowledge_context_builder: unrecognized field_code '%s' - excluded from context, no effect on payload.",
            field_code,
        )
        return None

    if entry["scope"] != expected_scope:
        logger.warning(
            "knowledge_context_builder: field_code '%s' registered for scope '%s' but rule row has "
            "knowledge_scope '%s' - excluded from context, no effect on payload.",
            field_code, entry["scope"], expected_scope,
        )
        return None

    return entry


def _collect_registered_fields(
    obj: Any, field_rules: List[Any], expected_scope: str
) -> Dict[str, Any]:
    """
    Shared collection logic for project/property/image scopes: for every
    Knowledge Rule row with a non-null field_code targeting expected_scope,
    resolve it against FIELD_RULE_REGISTRY and, if valid, read the named
    ORM attribute(s) off obj into the rule's context_key.

    field_rules is the list of DesignToolKnowledgeRule rows already
    filtered to this Tool and this scope (callers pass in exactly the
    rows relevant to one scope - this function does not query the
    database itself).
    """
    collected: Dict[str, Any] = {}
    for rule in field_rules:
        field_code = getattr(rule, "field_code", None)
        if not field_code:
            continue  # the blanket (field_code IS NULL) row is handled by LEGACY_SCOPE_FIELDS, not here

        entry = _resolve_field_rule(field_code, expected_scope)
        if entry is None:
            continue

        attributes = entry["attributes"]
        if len(attributes) == 1:
            collected[entry["context_key"]] = getattr(obj, attributes[0], None)
        else:
            # Composite field (e.g. PROJECT.BUDGET -> budget_low/budget_high)
            collected[entry["context_key"]] = {
                attr.replace(f"{entry['context_key']}_", ""): getattr(obj, attr, None)
                for attr in attributes
            }

    return collected


def build_project_knowledge_fields(project_obj: Any, field_rules: List[Any]) -> Dict[str, Any]:
    """Returns only the NEW (Phase 1.2A) project-scope fields explicitly
    granted via field_rules. Legacy fields (project_id/project_name/
    description) are not this function's responsibility - they remain
    exactly where payload_builder.py already builds them today."""
    return _collect_registered_fields(project_obj, field_rules, expected_scope="project")


def build_property_knowledge_fields(property_obj: Any, field_rules: List[Any]) -> Dict[str, Any]:
    """Returns only the NEW (Phase 1.2A) property-scope fields explicitly
    granted via field_rules. Legacy fields and ai_analysis are already
    handled by payload_builder.py / _build_property_ai_analysis()."""
    return _collect_registered_fields(property_obj, field_rules, expected_scope="property")


def build_image_knowledge_fields(image_obj: Any, field_rules: List[Any]) -> Dict[str, Any]:
    """Returns only the NEW (Phase 1.2A) image-scope fields explicitly
    granted via field_rules, for one PropertyImage object. Called once
    per selected image at Submit time (see the Submit-time-fresh image
    context change in payload_builder.py) - legacy per-image fields
    remain that call site's own responsibility, unchanged."""
    return _collect_registered_fields(image_obj, field_rules, expected_scope="image")


def build_design_job_knowledge_fields(design_job_obj: Any, field_rules: List[Any]) -> Dict[str, Any]:
    """Returns the design_job-scope fields explicitly granted via
    field_rules. design_job is a brand-new scope with zero legacy
    fields - LEGACY_SCOPE_FIELDS["design_job"] is intentionally empty,
    so every field surfaced here came through an explicit rule."""
    return _collect_registered_fields(design_job_obj, field_rules, expected_scope="design_job")


__all__ = [
    "LEGACY_SCOPE_FIELDS",
    "FIELD_RULE_REGISTRY",
    "build_project_knowledge_fields",
    "build_property_knowledge_fields",
    "build_image_knowledge_fields",
    "build_design_job_knowledge_fields",
]

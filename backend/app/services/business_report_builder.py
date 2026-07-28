"""
app/services/business_report_builder.py

AIHOME Result Rendering Framework v2 - Business Report Builder.

Per the simplified architecture: DEV-TOOLS is an AI Orchestration
Platform; AIHOME is a Business Application. AIHOME understands only Job,
Job History, Business Data, and Business Report - never Workflow
Templates, Workflow Versions, Parent/Child Workflows, Workflow Graphs,
Agents, Execution Order, or LLM Providers.

This module is where that interpretation now happens - moved here from
the frontend (which previously carried its own Semantic Shape Classifier
and Business Interpreter). The frontend's job is now reduced to rendering
a fixed, versioned Business Report JSON contract; ALL classification and
interpretation of DEV-TOOLS' raw output lives here, backend-side, where
it can be shared by any future presentation surface (mobile, PDF export,
a future admin view) without re-deriving it.

Pipeline (this module implements the middle two steps):

    DEV-TOOLS merged result
            v
    flatten_dev_tools_outputs()      [dev_tools_output_flattening.py]
            v
    classify + interpret             [THIS MODULE]
            v
    normalized Business Report JSON  (stored as PropertyAnalysisReport.report_json)
            v
    React frontend renders section.type generically

Business Report JSON contract (report_version "1.0"):

    {
      "report_type": str,           # e.g. "PROPERTY_INTELLIGENCE"
      "report_version": "1.0",
      "property": {...},            # AIHOME's own identifying data - NOT
                                     # derived from the AI output
      "executive_summary": str,
      "sections": [
        {"type": "property_overview", "title": str, "content": {...}},
        {"type": "risks", "title": str, "items": [RiskItem, ...]},
        {"type": "recommendations", "title": str, "items": [str, ...]},
        {"type": "priority_actions", "title": str, "items": [str, ...]},
      ],
      "confidence": str,
      "generated_at": ISO8601 str,
      "metadata": {...},
    }

    RiskItem: {"title": str, "severity": str|None, "detail": str|None,
               "evidence": [str, ...]|None}

Only output CONTENT is ever read here - never workflow_code, role,
execution_order, execution_mode, workflow_template_id, or
workflow_run_id. flatten_dev_tools_outputs() itself already strips these
away before this module ever sees a single output.
"""

import datetime
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.services.dev_tools_output_flattening import flatten_dev_tools_outputs

logger = logging.getLogger(__name__)

REPORT_VERSION = "1.0"

_NARRATIVE_NAME_HINTS = ("summary", "executive_summary", "description", "conclusion")
_CONFIRMED_LIST_KEY_PATTERN = re.compile(r"^confirmed_")
_ACTION_KEY_PATTERN = re.compile(r"action|priority_repair|immediate_attention|follow.?up|inspection_scope", re.I)
_RECOMMENDATION_KEY_PATTERN = re.compile(r"recommend", re.I)

_SEVERITY_RANK = {"critical": 0, "high": 0, "medium": 1, "low": 2}


# ---------------------------------------------------------------------------
# Layer 1 (ported): Semantic Shape Classifier - classifies one field VALUE
# by its structural shape, never by its name or which workflow produced
# it. Field names are used only as light heuristics (narrative vs. plain
# status string; which business bucket a list belongs in) - never as a
# lookup keyed to a workflow or agent identity.
# ---------------------------------------------------------------------------

def _classify_field(key: str, value: Any) -> Dict[str, Any]:
    if isinstance(value, str):
        looks_narrative = any(hint in key.lower() for hint in _NARRATIVE_NAME_HINTS) or len(value) > 120
        return {"kind": "narrative", "text": value} if looks_narrative else {"kind": "status", "value": value}

    if isinstance(value, list):
        if len(value) == 0:
            return {"kind": "string_list", "items": []}
        if isinstance(value[0], str):
            return {"kind": "string_list", "items": value}
        if isinstance(value[0], dict):
            return {"kind": "object_list", "items": value}
        return {"kind": "unknown", "value": value}

    if isinstance(value, dict):
        confirmed_key = next((k for k in value.keys() if _CONFIRMED_LIST_KEY_PATTERN.match(k)), None)
        if confirmed_key is not None:
            return {
                "kind": "status_list_object",
                "items": value.get(confirmed_key) or [],
                "status": value.get("status"),
                "reason": value.get("reason"),
            }
        if "status" in value or "condition" in value or "level" in value:
            return {
                "kind": "status_object",
                "status": str(value.get("status") or value.get("condition") or value.get("level") or ""),
                "confidence": value.get("confidence"),
                "reason": value.get("reason"),
            }
        return {"kind": "reference_data", "value": value}

    return {"kind": "unknown", "value": value}


# ---------------------------------------------------------------------------
# Text normalization + similarity-based deduplication (ported from
# businessInterpreter.ts's token-overlap approach)
# ---------------------------------------------------------------------------

def _normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[.,;:!?'\"()]", "", s.lower())).strip()


def _token_set(s: str) -> set:
    return {t for t in _normalize_text(s).split(" ") if len(t) > 2}


def _similarity(a: str, b: str) -> float:
    ta, tb = _token_set(a), _token_set(b)
    if not ta or not tb:
        return 0.0
    overlap = len(ta & tb)
    return overlap / min(len(ta), len(tb))


_SIMILARITY_MERGE_THRESHOLD = 0.5


def _dedupe_strings(items: List[str]) -> List[str]:
    """Merges near-duplicate strings, keeping the longest (most detailed)
    phrasing per cluster - e.g. two agents independently flagging the
    same underlying issue in different words collapse into one entry."""
    clusters: List[str] = []
    for item in items:
        match_idx = next((i for i, c in enumerate(clusters) if _similarity(c, item) >= _SIMILARITY_MERGE_THRESHOLD), None)
        if match_idx is not None:
            if len(item) > len(clusters[match_idx]):
                clusters[match_idx] = item
        else:
            clusters.append(item)
    return clusters


def _severity_rank(value: Optional[str]) -> int:
    if not value:
        return 3
    return _SEVERITY_RANK.get(value.lower(), 3)


def _humanize_label(key: str) -> str:
    return key.replace("_", " ").title()


def _looks_like_risk_finding(item: Dict[str, Any]) -> bool:
    """An objectList item only qualifies as a risk finding if it carries
    an EXPLICIT severity signal (severity / risk_level) - deliberately
    strict, so a bare validation object shaped like {code, message} is
    never mis-promoted to a "risk" with no real severity, and reference
    data (e.g. submitted-image objects) is never misclassified either."""
    return "severity" in item or "risk_level" in item


def _extract_finding_title(item: Dict[str, Any]) -> str:
    return str(item.get("title") or item.get("item") or item.get("issue") or item.get("message") or item.get("code") or "Finding")


def _extract_finding_severity(item: Dict[str, Any]) -> Optional[str]:
    raw = item.get("risk_level", item.get("severity"))
    return str(raw) if raw is not None else None


def _extract_finding_detail(item: Dict[str, Any]) -> Optional[str]:
    raw = item.get("reason") or item.get("why_high") or item.get("description") or item.get("message")
    return str(raw) if raw is not None else None


def _extract_finding_evidence(item: Dict[str, Any]) -> Optional[List[str]]:
    raw = item.get("evidence")
    return [str(e) for e in raw] if isinstance(raw, list) else None


# ---------------------------------------------------------------------------
# Layer 2 (ported): Business Interpreter
# ---------------------------------------------------------------------------

def _interpret(flattened_outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    narratives: List[Tuple[str, str]] = []  # (key, text)
    property_facts: Dict[str, Any] = {}
    condition_facts: Dict[str, str] = {}
    risk_findings_raw: List[Dict[str, Any]] = []
    recommendations_raw: List[str] = []
    actions_raw: List[str] = []

    for output in flattened_outputs:
        if output.get("output_type") != "json":
            continue
        content = output.get("content")
        if not isinstance(content, str):
            continue
        try:
            payload = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue

        for key, value in payload.items():
            shape = _classify_field(key, value)
            kind = shape["kind"]

            if kind == "narrative":
                narratives.append((key, shape["text"]))

            elif kind == "reference_data":
                for sub_key, sub_value in shape["value"].items():
                    if isinstance(sub_value, (str, int, float, bool)):
                        property_facts[_humanize_label(sub_key)] = sub_value

            elif kind == "status_object":
                condition_facts[_humanize_label(key)] = shape["status"]

            elif kind == "status_list_object":
                condition_facts[_humanize_label(key)] = shape["status"] or (
                    "Issues found" if shape["items"] else "No issues confirmed"
                )
                for raw_item in shape["items"]:
                    if isinstance(raw_item, dict) and _looks_like_risk_finding(raw_item):
                        risk_findings_raw.append(raw_item)

            elif kind == "object_list":
                for raw_item in shape["items"]:
                    if isinstance(raw_item, dict) and _looks_like_risk_finding(raw_item):
                        risk_findings_raw.append(raw_item)

            elif kind == "string_list":
                if _ACTION_KEY_PATTERN.search(key):
                    actions_raw.extend(shape["items"])
                elif _RECOMMENDATION_KEY_PATTERN.search(key):
                    recommendations_raw.extend(shape["items"])
                # Other string lists (e.g. missing_fields) are not
                # surfaced as risks or actions - available only via the
                # raw payload, never fabricated into a business section.

            # 'status' and 'unknown' shapes are not surfaced in the
            # normalized report - a bare status string or a shape this
            # classifier doesn't recognize isn't safe to interpret into
            # a business section on its own.

    # --- Executive summary: exactly one ---
    preferred = next((n for n in narratives if re.search(r"executive_summary|conclusion", n[0], re.I)), None)
    if preferred is None and narratives:
        preferred = max(narratives, key=lambda n: len(n[1]))
    executive_summary = preferred[1] if preferred else "No executive summary was provided for this analysis."

    # Any other narrative becomes a supporting property-overview fact
    # rather than being silently discarded.
    for key, text in narratives:
        if preferred is None or (key, text) != preferred:
            condition_facts[_humanize_label(key)] = text

    # --- Deduplicate + rank risk findings ---
    risk_items: List[Dict[str, Any]] = []
    for raw_item in risk_findings_raw:
        title = _extract_finding_title(raw_item)
        severity = _extract_finding_severity(raw_item)
        detail = _extract_finding_detail(raw_item)
        evidence = _extract_finding_evidence(raw_item)
        match_idx = next((i for i, r in enumerate(risk_items) if _similarity(r["title"], title) >= _SIMILARITY_MERGE_THRESHOLD), None)
        if match_idx is not None:
            if _severity_rank(severity) < _severity_rank(risk_items[match_idx]["severity"]):
                risk_items[match_idx]["severity"] = severity
        else:
            risk_items.append({"title": title, "severity": severity, "detail": detail, "evidence": evidence})
    risk_items.sort(key=lambda r: _severity_rank(r["severity"]))

    recommendations = _dedupe_strings(recommendations_raw)
    priority_actions = _dedupe_strings(actions_raw)

    # --- Overall confidence: the lowest (most cautious) confidence value
    # found among any status_object fields, defaulting to "Unknown" if
    # none were present - never fabricated. ---
    confidences = []
    for output in flattened_outputs:
        content = output.get("content")
        if not isinstance(content, str):
            continue
        try:
            payload = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        for key, value in payload.items():
            shape = _classify_field(key, value)
            if shape["kind"] == "status_object" and shape.get("confidence"):
                confidences.append(str(shape["confidence"]))
            if shape["kind"] == "status" and "confidence" in key.lower():
                confidences.append(str(shape["value"]))
    confidence_rank = {"low": 0, "medium": 1, "high": 2}
    overall_confidence = min(confidences, key=lambda c: confidence_rank.get(c.lower(), 1)) if confidences else "Unknown"

    return {
        "executive_summary": executive_summary,
        "property_facts": property_facts,
        "condition_facts": condition_facts,
        "risk_items": risk_items,
        "recommendations": recommendations,
        "priority_actions": priority_actions,
        "overall_confidence": overall_confidence,
    }


def build_business_report(
    result_data: Dict[str, Any],
    *,
    report_type: str,
    property_identity: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Builds the normalized Business Report JSON from a DEV-TOOLS result
    payload (either legacy flat-output shape or WIM Module V2 merged
    shape - flatten_dev_tools_outputs() handles both transparently).

    `property_identity` is AIHOME's OWN authoritative property data
    (e.g. {"property_id": ..., "address": ..., "property_uid": ...}),
    supplied by the caller (which already has the Property row loaded) -
    never derived from the AI output itself, since AIHOME owns Business
    Data and should not need to trust DEV-TOOLS' own restatement of it
    for identity purposes.

    Returns None if no narrative-shaped content was found anywhere in
    the payload (nothing report-worthy to build) - callers should treat
    this the same as "no recognized report shape" and fall back to
    existing malformed-output handling, never persisting an empty/
    fabricated report.
    """
    flattened = flatten_dev_tools_outputs(result_data)
    if not flattened:
        return None

    interpreted = _interpret(flattened)
    if interpreted["executive_summary"] == "No executive summary was provided for this analysis." and not interpreted["property_facts"]:
        # Nothing narrative or factual was found anywhere - this payload
        # genuinely has no report-worthy content for this contract.
        return None

    property_overview_content: Dict[str, Any] = dict(interpreted["property_facts"])
    property_overview_content.update(interpreted["condition_facts"])

    sections = [
        {"type": "property_overview", "title": "Property Overview", "content": property_overview_content},
        {"type": "risks", "title": "Key Risks", "items": interpreted["risk_items"]},
        {"type": "recommendations", "title": "Recommendations", "items": interpreted["recommendations"]},
        {"type": "priority_actions", "title": "Priority Actions", "items": interpreted["priority_actions"]},
    ]

    # WACP 1.1 / WIM Module V2: when the source outputs carry business_intent
    # provenance (flatten_dev_tools_outputs tags this from combined_outputs/
    # workflow_results - see that module's own docstring for the exact
    # conditions), surface the distinct set here, in first-seen order, so
    # a multi-intent job's report can note which Business Intents
    # contributed - satisfies "display combined workflow results
    # appropriately" without inventing new report sections or UI
    # structure beyond the existing Advanced Technical Details metadata
    # display. Absent entirely for a single-intent (WACP 1.0, or
    # single-intent WACP 1.1) job, matching this field's genuinely
    # optional nature.
    business_intents_seen: List[str] = []
    for output in flattened:
        intent = output.get("business_intent")
        if intent and intent not in business_intents_seen:
            business_intents_seen.append(intent)

    metadata: Dict[str, Any] = {"output_count": len(flattened)}
    if business_intents_seen:
        metadata["business_intents"] = business_intents_seen

    return {
        "report_type": report_type,
        "report_version": REPORT_VERSION,
        "property": property_identity or {},
        "executive_summary": interpreted["executive_summary"],
        "sections": sections,
        "confidence": interpreted["overall_confidence"],
        "generated_at": datetime.datetime.now().isoformat(),
        "metadata": metadata,
    }

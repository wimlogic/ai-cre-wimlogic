"""
AI-CRE WIMLOGIC V1 -- Phase 4 DEV-TOOLS Integration

result_sync.py

Centralizes ALL DEV-TOOLS -> AI-CRE result synchronization logic in one
reusable place. This module was extracted from the completion/failure
handling that previously lived inline inside
`ai_orchestration_service.receive_workflow_callback()` - the mapping logic
itself is unchanged, just relocated and extended.

Both the existing webhook callback path and any future polling path
(wacp_adapter.get_job_status / get_job_results) must call
`sync_job_result()` below as the single shared entrypoint, so there is
exactly one place that maps a DEV-TOOLS result payload onto AI-CRE tables.

Tables synchronized (all via existing CRUD/services - none invented here):
    - cre_workflow_executions        (workflow_execution_service)
    - cre_workflow_results           (workflow_result_service)
    - cre_property_analysis_reports  (workflow_result_service)
    - cre_generated_assets           (generated_asset_service)
    - cre_concept_designs            (crud.concept_design)           [new]
    - cre_estimates                  (crud.estimate)                 [new]
    - cre_zoning_notes               (crud.zoning_note)              [new]

No ORM sharing with DEV-TOOLS, no shared database - REST + JSON only, per
the Enterprise Payload / Result Contract. This module only ever receives
already-fetched JSON (from a webhook body or from
wacp_adapter.get_job_results()) and maps it onto existing AI-CRE models.
"""

import datetime
import json
import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

# Services (existing, unmodified)
from app.services.workflow_execution_service import workflow_execution_service
from app.services.workflow_result_service import workflow_result_service
from app.services.generated_asset_service import generated_asset_service

# CRUDs (existing, unmodified) - no dedicated service layer exists yet for
# these three tables, so they are called directly, same as elsewhere in
# this codebase for tables without a service wrapper.
from app.crud.project import project as crud_project
from app.crud.concept_design import concept_design as crud_concept_design
from app.crud.estimate import estimate as crud_estimate
from app.crud.zoning_note import zoning_note as crud_zoning_note

# Schemas (existing, unmodified)
from app.schemas.workflow_execution import WorkflowExecutionUpdate
from app.schemas.workflow_result import WorkflowResultCreate
from app.schemas.result_section import ResultSectionCreate
from app.schemas.property_analysis_report import PropertyAnalysisReportCreate
from app.schemas.generated_asset import GeneratedAssetCreate
from app.schemas.concept_design import ConceptDesignCreate
from app.schemas.estimate import EstimateCreate
from app.schemas.zoning_note import ZoningNoteCreate

# Models (existing, unmodified)
from app.models.workflow_execution import WorkflowExecution

logger = logging.getLogger(__name__)


class ResultSyncError(Exception):
    """Raised when a DEV-TOOLS result payload cannot be synchronized."""


# ---------------------------------------------------------------------------
# Natural-language Property Analysis report support
#
# DEV-TOOLS' PROPERTY_ANALYSIS workflow now returns:
#   executive_summary, key_findings, business_health, priority_actions,
#   recommendations, conclusion
# This is a genuinely different shape from the older
# result_data["property_analysis"] = {estimate_low, estimate_high,
# zoning_notes, risk_notes, recommendation, score} contract this module
# originally mapped - both are supported (§ backward compatibility),
# never one silently replacing the other's data.
# ---------------------------------------------------------------------------

_NL_REPORT_FIELDS = (
    "executive_summary",
    "key_findings",
    "business_health",
    "priority_actions",
    "recommendations",
    "conclusion",
)

# List-shaped fields render as bullets/numbered actions; the rest are
# paragraph prose. This distinction drives BOTH how `content` is encoded
# here (JSON array string vs raw text) and how the frontend renders it -
# the two must stay in agreement, which is why this tuple is the single
# source of truth for "which fields are lists" rather than being
# re-decided independently on each side.
_NL_REPORT_LIST_FIELDS = ("key_findings", "priority_actions", "recommendations")

_NL_REPORT_TITLES = {
    "executive_summary": "Executive Summary",
    "key_findings": "Key Findings",
    "business_health": "Business Health",
    "priority_actions": "Priority Actions",
    "recommendations": "Recommendations",
    "conclusion": "Conclusion",
}

# Fixed, natural reading order for the report - this drives
# ResultSection.display_order directly, rather than the order these keys
# happen to appear in the DEV-TOOLS JSON payload (dict key order in a
# parsed JSON object is not a contract DEV-TOOLS has made any promise
# about, and must not be relied upon for display ordering either).
_NL_REPORT_DISPLAY_ORDER = {field: i for i, field in enumerate(_NL_REPORT_FIELDS)}


def _select_final_output(result_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identifies the Final Property Analysis business result from a
    DEV-TOOLS /results response, per the WACP contract now verified
    directly by the DEV-TOOLS Platform Team (superseding this function's
    earlier, speculative "outputs/steps/step_results with is_final/
    sequence markers" design, which was built before that verification
    and did not match reality - the real Output records carry no such
    markers at all).

    The verified real shape: `result_data["outputs"]` is a list of
    `{"output_type", "title", "content"}` records, where `content` is a
    JSON-ENCODED STRING, not a nested dict. For PROPERTY_ANALYSIS there
    are currently two `output_type == "json"` entries - a Property
    Validation output and the Final Property Analysis - and the correct
    one is identified by its OWN content, never by array position: the
    parsed object containing `"executive_summary"` is the Final Property
    Analysis. Any other "json" output (e.g. Property Validation) is
    skipped here - see _extract_non_final_json_outputs() below, which
    persists it separately rather than discarding it outright.

    Falls back to two older shapes for backward compatibility with any
    already-persisted execution whose payload predates this verified
    contract - the legacy top-level "property_analysis" key, and a bare
    flat dict already carrying the natural-language fields directly.
    Neither of these is the real DEV-TOOLS contract; both remain only so
    a historical payload reprocessed through this path doesn't break.

    Returns the selected dict, or `result_data` unchanged if nothing
    recognized was found - callers detect "nothing usable" by checking
    the returned dict's own contents (see _sync_completed_job).
    """
    outputs = result_data.get("outputs")
    if isinstance(outputs, list):
        for output in outputs:
            if not isinstance(output, dict) or output.get("output_type") != "json":
                continue
            content = output.get("content")
            if not isinstance(content, str):
                continue
            try:
                parsed = json.loads(content)
            except (json.JSONDecodeError, TypeError) as exc:
                logger.warning(
                    "Skipping unparseable 'json' output (title=%r) while selecting the Final "
                    "Property Analysis: %s", output.get("title"), exc,
                )
                continue
            if isinstance(parsed, dict) and "executive_summary" in parsed:
                return parsed
        # An "outputs" list was present but no entry's parsed content
        # contained "executive_summary" - fall through to the legacy
        # checks below rather than assuming malformed outright.

    if "property_analysis" in result_data:
        return result_data

    if any(key in result_data for key in _NL_REPORT_FIELDS):
        return result_data

    return result_data


def _extract_non_final_json_outputs(result_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Returns every OTHER `output_type == "json"` entry from
    `result_data["outputs"]` besides the Final Property Analysis (e.g.
    the Property Validation output) - stored separately as their own
    ResultSection rows (§ "Validation output ignored (or stored
    separately if already supported)" - it IS already supported, via the
    existing generic ResultSection shape, so this stores rather than
    discards). Identifies the Final Property Analysis the same way
    _select_final_output() does (presence of "executive_summary"), so
    the two functions can never disagree about which output is which.
    Each entry's `content` is parsed if it's valid JSON; otherwise the
    raw string is kept as-is rather than dropping the output entirely.
    """
    outputs = result_data.get("outputs")
    if not isinstance(outputs, list):
        return []

    extras: List[Dict[str, Any]] = []
    for output in outputs:
        if not isinstance(output, dict) or output.get("output_type") != "json":
            continue
        content = output.get("content")
        if not isinstance(content, str):
            continue
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            parsed = None
        if isinstance(parsed, dict) and "executive_summary" in parsed:
            continue  # this is the Final Property Analysis, already handled elsewhere - skip
        extras.append({
            "title": output.get("title") or "Additional Output",
            "content": json.dumps(parsed) if parsed is not None else content,
        })
    return extras


def _build_natural_language_report_sections(output: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Maps a selected output dict's natural-language report fields into the
    exact shape workflow_result_service.create_section() / ResultSectionCreate
    expects - one dict per field ACTUALLY PRESENT in `output` (a missing
    field produces no entry at all, never a placeholder/empty section, per
    the approved "hide missing sections" behavior).

    List-shaped fields (_NL_REPORT_LIST_FIELDS) are JSON-encoded into
    `content` as a JSON array string, so the frontend can render them as
    bullets/numbered actions; paragraph fields are stored as plain text.
    `display_order` is the fixed natural reading order (_NL_REPORT_
    DISPLAY_ORDER), not whatever order the fields happened to appear in
    the source JSON.
    """
    sections = []
    for field in _NL_REPORT_FIELDS:
        if field not in output or output[field] is None:
            continue

        value = output[field]
        if field in _NL_REPORT_LIST_FIELDS:
            if not isinstance(value, list):
                # A list-shaped field arrived as something else (e.g. a
                # single string) - normalize into a one-item list rather
                # than silently coercing it into prose or dropping it.
                value = [value]
            content = json.dumps(value)
        else:
            content = value if isinstance(value, str) else json.dumps(value)

        sections.append({
            "section_type": field,
            "title": _NL_REPORT_TITLES[field],
            "content": content,
            "display_order": _NL_REPORT_DISPLAY_ORDER[field],
        })
    return sections


def _sync_concept_designs(
    db: Session, *, execution: WorkflowExecution, project_id_str: str, concept_designs_data: List[Dict[str, Any]]
) -> None:
    for item in concept_designs_data:
        design_in = ConceptDesignCreate(
            project_id=project_id_str,
            property_id=execution.property_id,
            scenario_id=execution.scenario_id,
            title=item.get("title"),
            concept_prompt=item.get("concept_prompt", ""),
            concept_notes=item.get("concept_notes"),
            image_reference_ids=item.get("image_reference_ids"),
            status=item.get("status", "draft"),
            workflow_execution_id=execution.execution_id,
            design_version=item.get("design_version"),
        )
        crud_concept_design.create(db, obj_in=design_in)


def _sync_estimates(
    db: Session, *, execution: WorkflowExecution, estimates_data: List[Dict[str, Any]], result_version: str
) -> None:
    for item in estimates_data:
        estimate_in = EstimateCreate(
            property_id=execution.property_id,
            scenario=item.get("scenario", "DEV-TOOLS Estimate"),
            proposed_use=item.get("proposed_use"),
            proposed_building_sqft=item.get("proposed_building_sqft"),
            proposed_units=item.get("proposed_units"),
            low_cost=item.get("low_cost"),
            mid_cost=item.get("mid_cost"),
            high_cost=item.get("high_cost"),
            cost_per_sqft_low=item.get("cost_per_sqft_low"),
            cost_per_sqft_high=item.get("cost_per_sqft_high"),
            assumptions=item.get("assumptions"),
            risk_level=item.get("risk_level", "medium"),
            workflow_execution_id=execution.execution_id,
            estimate_source="DEV-TOOLS",
            estimate_version=result_version,
        )
        crud_estimate.create(db, obj_in=estimate_in)


def _sync_zoning_notes(
    db: Session, *, execution: WorkflowExecution, zoning_notes_data: List[Dict[str, Any]]
) -> None:
    for item in zoning_notes_data:
        zoning_note_in = ZoningNoteCreate(
            property_id=execution.property_id,
            zoning_code=item.get("zoning_code"),
            allowed_use_summary=item.get("allowed_use_summary"),
            conditional_use_notes=item.get("conditional_use_notes"),
            parking_notes=item.get("parking_notes"),
            entitlement_risk=item.get("entitlement_risk", "medium"),
            source_url=item.get("source_url"),
        )
        crud_zoning_note.create(db, obj_in=zoning_note_in)


def _sync_completed_job(
    db: Session, *, execution: WorkflowExecution, payload: Dict[str, Any]
) -> WorkflowExecution:
    """
    Handles a "completed" DEV-TOOLS result payload. Steps 1-4 (workflow
    result, result sections, property analysis report, generated assets)
    are unchanged from the original inline logic in
    ai_orchestration_service.receive_workflow_callback(); steps 5-7
    (concept designs, estimates, zoning notes) are new, per the Phase 4
    extension.
    """
    result_version = payload.get("version", "1.0.0")
    # Verified DEV-TOOLS contract (confirmed directly by the DEV-TOOLS
    # Platform Team): "outputs" sits at `payload`'s OWN top level -
    # `payload` already IS `response.result` directly (see
    # wacp_adapter._normalize()), not a further-nested "results" wrapper.
    # The legacy pre-verification assumption (business fields living
    # under payload["results"]) is preserved ONLY as a fallback for any
    # already-persisted historical payload that predates this contract -
    # never used when "outputs" is actually present.
    result_data = payload if "outputs" in payload else payload.get("results", {})

    # 1. Create Raw Workflow Result
    result_in = WorkflowResultCreate(
        execution_id=execution.execution_id,
        result_type=execution.workflow_code,
        result_version=result_version,
        response_json=json.dumps(result_data),
        normalized=1,
    )
    result_obj = workflow_result_service.create_result(db, result_in=result_in)

    # 2. Parse payload and register structured Result Sections.
    #
    # The generic sections_data loop below is unchanged, pre-existing
    # behavior for whatever legacy `result_data["sections"]` list a
    # payload may still carry. The natural-language Property Analysis
    # report fields (executive_summary, key_findings, business_health,
    # priority_actions, recommendations, conclusion) are a SEPARATE,
    # additive concern handled just below it - both can coexist on the
    # same WorkflowResult without conflict, since ResultSection rows are
    # simply additive per result_id.
    sections_data: List[Dict[str, Any]] = result_data.get("sections", [])
    for sec in sections_data:
        sec_in = ResultSectionCreate(
            result_id=result_obj.result_id,
            section_type=sec.get("section_type", "analysis"),
            title=sec.get("title", "Analysis Details"),
            content=sec.get("content", ""),
            confidence_score=sec.get("confidence_score"),
        )
        workflow_result_service.create_section(db, section_in=sec_in)

    # 2b. Natural-language Property Analysis report (verified DEV-TOOLS
    # PROPERTY_ANALYSIS output contract: result_data["outputs"] is a list
    # of {"output_type","title","content"} records; content is a JSON
    # string). Deterministically identify the Final Property Analysis
    # first (§ _select_final_output - by content, never array position),
    # then create one ResultSection per report field ACTUALLY PRESENT -
    # a missing field is simply skipped, never rendered as an empty
    # section.
    final_output = _select_final_output(result_data)

    nl_report_sections = _build_natural_language_report_sections(final_output)
    if nl_report_sections:
        for sec_dict in nl_report_sections:
            workflow_result_service.create_section(
                db, section_in=ResultSectionCreate(result_id=result_obj.result_id, **sec_dict)
            )
    elif "property_analysis" not in final_output and not sections_data:
        # Malformed/unrecognized output: neither the new natural-language
        # fields, the legacy property_analysis key, nor a sections list
        # were found anywhere. Never silently discarded - the full raw
        # payload is still preserved in report_json/response_json
        # regardless (steps 1 and 3), and a single clearly-labeled
        # fallback section makes that visible in the UI too, rather than
        # presenting an empty report with no indication anything is wrong.
        logger.warning(
            "No recognized report shape (natural-language fields, legacy property_analysis, or "
            "sections) found for execution_id=%s. Persisting raw payload only.",
            execution.execution_id,
        )
        workflow_result_service.create_section(
            db,
            section_in=ResultSectionCreate(
                result_id=result_obj.result_id,
                section_type="unrecognized_output",
                title="Unrecognized Output Format",
                content=json.dumps(result_data),
                display_order=0,
            ),
        )

    # 2c. Any OTHER "json" output alongside the Final Property Analysis
    # (currently: the Property Validation output) - stored separately
    # rather than discarded, reusing the same generic ResultSection
    # shape, per "Validation output ignored (or stored separately if
    # already supported)".
    for extra in _extract_non_final_json_outputs(result_data):
        workflow_result_service.create_section(
            db,
            section_in=ResultSectionCreate(
                result_id=result_obj.result_id,
                section_type="supplementary_output",
                title=extra["title"],
                content=extra["content"],
                display_order=len(_NL_REPORT_FIELDS),
            ),
        )

    # 3. Extract and populate high-level Business Property Analysis Report.
    #
    # Two supported shapes, never one silently overwriting the other's
    # data: the new natural-language report (report_json gets the full
    # selected output; the narrow legacy numeric/text columns are left
    # unset since they don't apply to this shape) and the legacy
    # `property_analysis` shape (unchanged from the original mapping).
    project_obj = crud_project.get(db, execution.project_id)
    project_id_str = project_obj.project_id if project_obj else "unknown"

    if any(k in final_output for k in _NL_REPORT_FIELDS):
        # New shape. `recommendation` is set from `conclusion` as the
        # closest single-field legacy equivalent (a short top-line
        # takeaway) for any older code still reading that one column -
        # the full detail lives in report_json and the ResultSection rows
        # above, not squeezed into the narrow legacy fields.
        report_in = PropertyAnalysisReportCreate(
            project_id=project_id_str,
            property_id=execution.property_id,
            scenario_id=execution.scenario_id,
            estimate_low=None,
            estimate_high=None,
            zoning_notes=None,
            risk_notes=None,
            recommendation=final_output.get("conclusion"),
            score=None,
            report_json=final_output,
            workflow_execution_id=execution.execution_id,
            workflow_result_id=result_obj.result_id,
            analysis_version=result_version,
            confidence_score=payload.get("confidence_score"),
            workflow_status="Completed",
            completed_at=datetime.datetime.now(),
        )
    else:
        # Legacy shape - unchanged from the original mapping.
        report_data = result_data.get("property_analysis", {})
        report_in = PropertyAnalysisReportCreate(
            project_id=project_id_str,
            property_id=execution.property_id,
            scenario_id=execution.scenario_id,
            estimate_low=report_data.get("estimate_low"),
            estimate_high=report_data.get("estimate_high"),
            zoning_notes=report_data.get("zoning_notes"),
            risk_notes=report_data.get("risk_notes"),
            recommendation=report_data.get("recommendation"),
            score=report_data.get("score"),
            report_json=report_data,
            workflow_execution_id=execution.execution_id,
            workflow_result_id=result_obj.result_id,
            analysis_version=result_version,
            confidence_score=payload.get("confidence_score"),
            workflow_status="Completed",
            completed_at=datetime.datetime.now(),
        )
    workflow_result_service.create_report(db, report_in=report_in)

    # 4. Populate associated Assets generated by the workflow (e.g. PDF briefs).
    # Per the standard Enterprise Result Contract, generated_assets lives
    # inside `results`, alongside estimates/zoning/concept_designs.
    assets_data: List[Dict[str, Any]] = result_data.get("generated_assets", [])
    for asset in assets_data:
        asset_in = GeneratedAssetCreate(
            execution_id=execution.execution_id,
            property_id=execution.property_id,
            asset_type=asset.get("asset_type", "pdf"),
            asset_category=asset.get("asset_category", "brief"),
            title=asset.get("title", "Generated Brief"),
            description=asset.get("description"),
            file_name=asset.get("file_name", "analysis_brief.pdf"),
            storage_path=asset.get("storage_path", "/assets/default.pdf"),
            thumbnail_path=asset.get("thumbnail_path"),
            mime_type=asset.get("mime_type", "application/pdf"),
            file_size=asset.get("file_size"),
            version=result_version,
        )
        generated_asset_service.create_asset(db, asset_in=asset_in)

    # 5. NEW - Concept Designs
    _sync_concept_designs(
        db,
        execution=execution,
        project_id_str=project_id_str,
        concept_designs_data=result_data.get("concept_designs", []),
    )

    # 6. NEW - Cost Estimates
    _sync_estimates(
        db,
        execution=execution,
        estimates_data=result_data.get("estimates", []),
        result_version=result_version,
    )

    # 7. NEW - Zoning Notes
    _sync_zoning_notes(
        db,
        execution=execution,
        zoning_notes_data=result_data.get("zoning", []),
    )

    # 8. Complete execution lifecycle state.
    # Normalizes a legacy omission: previously this only logged an event
    # with status="Completed" without updating the execution row's own
    # `.status` column, unlike the failure path below (which does call
    # update_execution). Since result_sync.py is now the single
    # synchronization implementation, this is corrected here so both
    # completion and failure consistently update execution state the
    # same way.
    update_in = WorkflowExecutionUpdate(
        status="Completed",
        completed_at=datetime.datetime.now(),
    )
    workflow_execution_service.update_execution(db, execution_id=execution.execution_id, execution_in=update_in)

    workflow_execution_service.add_event(
        db,
        execution_id=execution.execution_id,
        event_type="SYSTEM",
        status="Completed",
        message="Workflow analysis successfully processed. Reports and generated assets have been cached.",
    )

    db.refresh(execution)
    return execution


def _sync_failed_job(
    db: Session, *, execution: WorkflowExecution, error_message: str
) -> WorkflowExecution:
    """Handles a "failed" DEV-TOOLS result payload. Unchanged from the
    original inline logic in ai_orchestration_service.receive_workflow_callback()."""
    update_in = WorkflowExecutionUpdate(
        status="Failed",
        error_message=error_message,
        completed_at=datetime.datetime.now(),
    )
    workflow_execution_service.update_execution(db, execution_id=execution.execution_id, execution_in=update_in)

    workflow_execution_service.add_event(
        db,
        execution_id=execution.execution_id,
        event_type="SYSTEM",
        status="Failed",
        message=f"Orchestrator returned failure: {error_message}",
    )

    db.refresh(execution)
    return execution


def sync_job_result(
    db: Session, *, execution: WorkflowExecution, status: str, payload: Dict[str, Any]
) -> WorkflowExecution:
    """
    Single shared entrypoint for synchronizing a DEV-TOOLS job result into
    AI-CRE tables, regardless of how the result arrived (webhook callback
    today; future polling via wacp_adapter.get_job_results() will call
    this exact same function with the same payload shape).

    Already-finalized executions (Completed/Failed) are returned unchanged,
    matching the existing idempotency guard from the original callback.
    """
    if execution.status in ("Completed", "Failed"):
        return execution

    if status.lower() == "completed":
        return _sync_completed_job(db, execution=execution, payload=payload)

    error_msg = payload.get("error_message", "Unknown WIMLOGIC orchestrator execution error.")
    return _sync_failed_job(db, execution=execution, error_message=error_msg)

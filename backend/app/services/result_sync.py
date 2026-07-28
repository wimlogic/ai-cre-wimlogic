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
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

# Services (existing, unmodified)
from app.services.workflow_execution_service import workflow_execution_service
from app.services.workflow_result_service import workflow_result_service
from app.services.generated_asset_service import generated_asset_service
from app.services.dev_tools_output_flattening import flatten_dev_tools_outputs

# CRUDs (existing, unmodified) - no dedicated service layer exists yet for
# these three tables, so they are called directly, same as elsewhere in
# this codebase for tables without a service wrapper.
from app.crud.project import project as crud_project
from app.crud.property import property as crud_property
from app.crud.concept_design import concept_design as crud_concept_design
from app.crud.estimate import estimate as crud_estimate
from app.crud.zoning_note import zoning_note as crud_zoning_note

from app.services.business_report_builder import build_business_report

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
from app.models.workflow_result import WorkflowResult
from app.models.property_analysis_report import PropertyAnalysisReport

from app.crud.property_analysis_report import property_analysis_report as crud_property_analysis_report
from app.schemas.property_analysis_report import PropertyAnalysisReportUpdate

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

    Also transparently supports the WIM Module V2 merged shape, where
    `result_data["outputs"]` contains a single wrapper entry whose own
    content holds a `workflows` list of nested outputs -
    flatten_dev_tools_outputs() unwraps that structure first, so this
    function's own selection logic (by content, never by array position,
    never by which workflow produced it) is completely unchanged and
    applies identically either way.

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
    for output in flatten_dev_tools_outputs(result_data):
        if output.get("output_type") != "json":
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
    # No entry's parsed content (flat or unwrapped from a WIM V2
    # wrapper) contained "executive_summary" - fall through to the
    # legacy checks below rather than assuming malformed outright.

    if "property_analysis" in result_data:
        return result_data

    if any(key in result_data for key in _NL_REPORT_FIELDS):
        return result_data

    return result_data


def _extract_non_final_json_outputs(result_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Returns every OTHER `output_type == "json"` entry (besides the Final
    Property Analysis) from the normalized output list -
    flatten_dev_tools_outputs() unwraps a WIM Module V2 wrapper the same
    way _select_final_output() does, so for a WIM V2 job this naturally
    includes every child workflow's own output (e.g. Damage Detection,
    Room Classification, Property Risk), not just a legacy Property
    Validation output - all stored as their own ResultSection rows (§
    "Validation output ignored (or stored separately if already
    supported)" - it IS already supported, via the existing generic
    ResultSection shape, so this stores rather than discards). Identifies
    the Final Property Analysis the same way _select_final_output() does
    (presence of "executive_summary"), so the two functions can never
    disagree about which output is which. Each entry's `content` is
    parsed if it's valid JSON; otherwise the raw string is kept as-is
    rather than dropping the output entirely.
    """
    extras: List[Dict[str, Any]] = []
    for output in flatten_dev_tools_outputs(result_data):
        if output.get("output_type") != "json":
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
    db: Session, *, execution: WorkflowExecution, payload: Dict[str, Any], local_status: str = "Completed"
) -> WorkflowExecution:
    """
    Handles a "completed" DEV-TOOLS result payload. Steps 1-4 (workflow
    result, result sections, property analysis report, generated assets)
    are unchanged from the original inline logic in
    ai_orchestration_service.receive_workflow_callback(); steps 5-7
    (concept designs, estimates, zoning notes) are new, per the Phase 4
    extension.

    `local_status` is the exact execution-status string this job
    completed as - "Completed" (the default, and the only value used by
    any pre-existing caller) or "Completed with Warnings" (WIM Module V2's
    COMPLETED_WITH_WARNINGS terminal state, mapped by
    ai_orchestration_service._map_remote_status). Every step of the
    synchronization below (workflow result, sections, reports, assets) is
    identical either way - only the final execution.status write at the
    end of this function reflects which one actually happened.
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
    #
    # WACP 1.1 / WIM Module V2 (backend/wacp/WACP_PROTOCOL_1_1.md): a
    # terminal result may instead carry `combined_outputs` and/or
    # `workflow_results` at this SAME top level, with `outputs` present
    # only as a backward-compatible alias - which the spec's own example
    # always shows populated alongside them, but is not guaranteed
    # non-empty in every real response. Recognizing either key here
    # (not just "outputs") ensures `result_data` is `payload` itself
    # whenever ANY of the three business-content keys is present -
    # otherwise a combined_outputs/workflow_results-only payload would
    # incorrectly collapse to {} before flatten_dev_tools_outputs (which
    # already handles all three) ever sees it.
    result_data = (
        payload
        if any(key in payload for key in ("outputs", "combined_outputs", "workflow_results"))
        else payload.get("results", {})
    )

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
        #
        # report_json now holds the normalized Business Report JSON
        # (business_report_builder.build_business_report), not the raw
        # final_output dict - per the simplified architecture, AIHOME's
        # backend is where DEV-TOOLS' output gets interpreted into one
        # business report; the frontend only renders section.type
        # generically from here on. property_identity is AIHOME's OWN
        # Property row data, not derived from the AI output, since
        # AIHOME owns Business Data.
        property_obj = crud_property.get(db, execution.property_id)
        property_identity = (
            {
                "property_id": property_obj.id,
                "property_uid": property_obj.property_uid,
                "address": property_obj.address,
            }
            if property_obj else {}
        )
        business_report = build_business_report(result_data, report_type=execution.workflow_code, property_identity=property_identity)
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
            report_json=business_report if business_report is not None else final_output,
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

    # 3b. AIHOME Image Result Integration - IMAGE_DESIGN workflow support.
    # Eager import, at sync time, not lazily when a user opens the
    # Results page. THIS CALL WAS CONFIRMED MISSING FROM THIS FILE -
    # design_result_service.ingest_image_design_results() has been
    # correct and fully tested for several sessions, but was never
    # actually invoked from anywhere in the real job-completion path,
    # which is why no IMAGE_DESIGN result has ever been imported despite
    # every other piece of the pipeline working correctly in isolation.
    # A result with no design_images at all (the overwhelming majority
    # of jobs) is a cheap no-op here.
    from app.services.design_result_service import ingest_image_design_results
    ingest_image_design_results(db, execution=execution, result_data=result_data)

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
    # same way. Uses local_status (not a hardcoded "Completed") so a
    # COMPLETED_WITH_WARNINGS job correctly ends up displayed as
    # "Completed with Warnings", not silently collapsed to "Completed".
    update_in = WorkflowExecutionUpdate(
        status=local_status,
        completed_at=datetime.datetime.now(),
    )
    workflow_execution_service.update_execution(db, execution_id=execution.execution_id, execution_in=update_in)

    workflow_execution_service.add_event(
        db,
        execution_id=execution.execution_id,
        event_type="SYSTEM",
        status=local_status,
        message=(
            "Workflow analysis successfully processed. Reports and generated assets have been cached."
            if local_status == "Completed"
            else "Workflow analysis processed with warnings. Reports and generated assets have been cached."
        ),
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

    Already-finalized executions (Completed/Completed with Warnings/
    Failed/Cancelled - the two "Completed" variants are exempted from
    the *second* fetch+sync no less than the original single-status
    guard was) are returned unchanged, matching the existing idempotency
    guard from the original callback.

    `status` may arrive in either of two forms depending on caller: the
    webhook callback (receive_workflow_callback) passes DEV-TOOLS' own
    raw wire-format string verbatim (any casing - "COMPLETED",
    "completed", "Completed with warnings", etc.), while polling
    (check_workflow_status) passes the value already normalized through
    ai_orchestration_service._map_remote_status (e.g. "Completed with
    Warnings", Title Case). Both terminal-success spellings are matched
    case-insensitively here for exactly that reason - this function
    cannot assume its caller already normalized the string. A tiny,
    local two-entry mapping is used rather than importing
    _map_remote_status from ai_orchestration_service, which already
    imports FROM this module (result_sync.sync_job_result) - reusing it
    here would create a circular import for the sake of two string
    comparisons.
    """
    if execution.status in ("Completed", "Completed with Warnings", "Failed", "Cancelled"):
        return execution

    # Normalizes both the raw DEV-TOOLS wire format (underscore-separated,
    # e.g. "COMPLETED_WITH_WARNINGS") and the already-mapped local display
    # form (space-separated, e.g. "Completed with Warnings") to the same
    # comparable string - the webhook callback passes the former
    # verbatim; polling passes the latter (already run through
    # _map_remote_status). Without this, a raw webhook callback for
    # COMPLETED_WITH_WARNINGS would fail to match and incorrectly fall
    # through to the failure path below.
    normalized = status.strip().lower().replace("_", " ")
    if normalized == "completed with warnings":
        return _sync_completed_job(db, execution=execution, payload=payload, local_status="Completed with Warnings")
    if normalized == "completed":
        return _sync_completed_job(db, execution=execution, payload=payload, local_status="Completed")

    error_msg = payload.get("error_message", "Unknown WIMLOGIC orchestrator execution error.")
    return _sync_failed_job(db, execution=execution, error_message=error_msg)


def _is_normalized_business_report(candidate: Any) -> bool:
    """
    Recognizes the normalized Business Report JSON contract
    (report_version "1.0") by shape, so a PropertyAnalysisReport whose
    report_json predates this contract (the raw flat final_output dict a
    pre-fix result_sync.py stored, or a legacy `property_analysis`-shape
    row) is never mistaken for an already-built report. Checking for the
    presence of "sections" as a list is sufficient and intentionally
    lightweight - this is a shape check, not full schema validation.
    """
    return isinstance(candidate, dict) and isinstance(candidate.get("sections"), list)


def get_or_build_business_report(db: Session, *, workflow_result_id: int) -> Optional[Dict[str, Any]]:
    """
    The one place AIHOME loads a Business Report for a WorkflowResult -
    used by the API layer (GET /workflow-results/{id}/business-report)
    and by anything else that needs "the report for this result",
    present or historical.

        Load Workflow Result
                v
        Does a normalized PropertyAnalysisReport already exist?
          YES -> use it
          NO  -> build one from the stored response_json
                 (business_report_builder.build_business_report -
                 the exact same deterministic builder used at sync time)
                 -> persist it for future requests (best-effort; a
                    missing property association skips the write but
                    still returns the built report)
        Continue rendering normally either way.

    This closes the "two generations of reports" gap: a job processed
    before WIM V2 support existed (report_json missing, or in the old
    raw-final-output shape) is rebuilt on first request from its already-
    stored response_json - no reprocessing, no migration, no re-running
    the original DEV-TOOLS job. build_business_report() is a pure
    function of its input (classification and interpretation carry no
    hidden state), so calling this twice for the same stored
    response_json always produces the same report content - the only
    field that legitimately differs between calls is `generated_at`,
    which reflects when THIS build happened, same as any cache
    timestamp.

    Returns None only if no WorkflowResult exists for this ID, or its
    stored response_json cannot be parsed/interpreted into any report at
    all (the same "nothing recognized" case _sync_completed_job already
    handles at sync time).
    """
    result_obj = db.get(WorkflowResult, workflow_result_id)
    if result_obj is None:
        return None

    existing = crud_property_analysis_report.get_multi(db, workflow_result_id=workflow_result_id, limit=1)[0]
    existing_report = existing[0] if existing else None
    if existing_report is not None and _is_normalized_business_report(existing_report.report_json):
        return existing_report.report_json

    if not result_obj.response_json:
        return None
    try:
        result_data = json.loads(result_obj.response_json)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Cannot rebuild business report for workflow_result_id=%s: response_json is not valid JSON.", workflow_result_id)
        return None

    execution = db.get(WorkflowExecution, result_obj.execution_id)
    property_obj = crud_property.get(db, execution.property_id) if execution and execution.property_id else None
    property_identity = (
        {"property_id": property_obj.id, "property_uid": property_obj.property_uid, "address": property_obj.address}
        if property_obj else {}
    )
    report_type = (execution.workflow_code if execution else None) or result_obj.result_type

    business_report = build_business_report(result_data, report_type=report_type, property_identity=property_identity)
    if business_report is None:
        return None

    # Persist for future requests - best-effort. PropertyAnalysisReport.
    # property_id is NOT NULL, so a result whose execution has no
    # property association cannot be persisted this way; the freshly
    # built report is still returned so rendering succeeds regardless.
    if execution and execution.property_id:
        project_obj = crud_project.get(db, execution.project_id) if execution.project_id else None
        project_id_str = project_obj.project_id if project_obj else "unknown"
        try:
            if existing_report is not None:
                # A row exists but predates the normalized contract (old
                # raw-final-output shape) - update it in place rather
                # than creating a second, duplicate report row for the
                # same workflow_result_id.
                crud_property_analysis_report.update(
                    db, db_obj=existing_report,
                    obj_in=PropertyAnalysisReportUpdate(report_json=business_report),
                )
            else:
                report_in = PropertyAnalysisReportCreate(
                    project_id=project_id_str,
                    property_id=execution.property_id,
                    scenario_id=execution.scenario_id,
                    recommendation=business_report.get("executive_summary"),
                    report_json=business_report,
                    workflow_execution_id=execution.execution_id,
                    workflow_result_id=workflow_result_id,
                    analysis_version=result_obj.result_version,
                    workflow_status="Completed",
                    completed_at=result_obj.received_at,
                )
                workflow_result_service.create_report(db, report_in=report_in)
        except Exception:
            # Persistence is explicitly best-effort per the approved
            # design ("(Optional) Persist... for future requests") - a
            # failure here must never prevent the already-built report
            # from being returned and rendered this request.
            logger.exception(
                "Failed to persist lazily-built business report for workflow_result_id=%s; "
                "returning the built report without persisting it.", workflow_result_id,
            )
            db.rollback()

    return business_report

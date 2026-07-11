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
    result_data = payload.get("results", {})

    # 1. Create Raw Workflow Result
    result_in = WorkflowResultCreate(
        execution_id=execution.execution_id,
        result_type=execution.workflow_code,
        result_version=result_version,
        response_json=json.dumps(result_data),
        normalized=1,
    )
    result_obj = workflow_result_service.create_result(db, result_in=result_in)

    # 2. Parse payload and register structured Result Sections
    sections_data: List[Dict[str, Any]] = result_data.get("sections", [])
    for sec in sections_data:
        sec_in = ResultSectionCreate(
            result_id=result_obj.result_id,
            section_type=sec.get("section_type", "analysis"),
            title=sec.get("title", "Analysis Details"),
            content=sec.get("content", ""),
            confidence_score=sec.get("confidence_score"),
            metadata_json=sec.get("metadata", {}),
        )
        workflow_result_service.create_section(db, section_in=sec_in)

    # 3. Extract and populate high-level Business Property Analysis Report
    project_obj = crud_project.get(db, execution.project_id)
    project_id_str = project_obj.project_id if project_obj else "unknown"

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

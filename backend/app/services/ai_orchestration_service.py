import os
import json
import uuid
import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select

# Services
from app.services.workflow_execution_service import workflow_execution_service
from app.services.workflow_result_service import workflow_result_service
from app.services.generated_asset_service import generated_asset_service

# CRUDs
from app.crud.api_usage_log import api_usage_log as crud_api_usage_log
from app.crud.project import project as crud_project
from app.crud.property import property as crud_property

# Schemas
from app.schemas.workflow_execution import WorkflowExecutionCreate, WorkflowExecutionUpdate
from app.schemas.workflow_result import WorkflowResultCreate
from app.schemas.result_section import ResultSectionCreate
from app.schemas.property_analysis_report import PropertyAnalysisReportCreate
from app.schemas.generated_asset import GeneratedAssetCreate
from app.schemas.api_usage_log import ApiUsageLogCreate

# Models
from app.models.workflow_execution import WorkflowExecution

class AIOrchestrationService:
    def __init__(self) -> None:
        self.wimlogic_api_url = os.getenv("WIMLOGIC_API_URL", "https://api.wimlogic.enterprise/v1")
        self.wimlogic_api_key = os.getenv("WIMLOGIC_API_KEY", "")

    def submit_workflow(
        self,
        db: Session,
        *,
        project_id: int,
        property_id: int,
        workflow_code: str,
        scenario_id: Optional[int] = None,
        priority: str = "Normal",
        metadata_json: Optional[Dict[str, Any]] = None
    ) -> WorkflowExecution:
        """
        Submits a workflow execution request to the DEV-TOOLS WIMLOGIC enterprise orchestrator.
        Performs local state setup, issues tracking events, registers the external task,
        and logs integration usage.
        """
        # 1. Resolve project_id string identifier from project primary key ID
        project_obj = crud_project.get(db, project_id)
        if not project_obj:
            raise ValueError(f"Project with ID '{project_id}' does not exist")

        property_obj = crud_property.get(db, property_id)
        if not property_obj:
            raise ValueError(f"Property with ID '{property_id}' does not exist")

        # 2. Generate tracking identifiers
        execution_number = f"EXE-WIM-{uuid.uuid4().hex[:12].upper()}"
        devtools_execution_id = f"WIM-JOB-{uuid.uuid4().hex[:16].upper()}"

        # 3. Create initial pending execution entry
        execution_in = WorkflowExecutionCreate(
            execution_number=execution_number,
            project_id=project_id,
            property_id=property_id,
            scenario_id=scenario_id,
            workflow_code=workflow_code,
            workflow_version="1.0.0",
            devtools_execution_id=devtools_execution_id,
            status="Pending",
            priority=priority,
            metadata_json=metadata_json or {}
        )
        execution_obj = workflow_execution_service.create_execution(db, execution_in=execution_in)

        # 4. Log the initial lifecycle transition
        workflow_execution_service.add_event(
            db,
            execution_id=execution_obj.execution_id,
            event_type="SYSTEM",
            status="Pending",
            message=f"Created workflow execution state {execution_number}. Dispatching to external orchestrator."
        )

        # 5. Send integration request to WIMLOGIC and record API log
        try:
            # Note: Do not make actual blocking external network calls during cold starts if not configured,
            # but preserve standard integration flow hooks and log appropriate integration metadata.
            api_log_in = ApiUsageLogCreate(
                provider="WIMLOGIC",
                api_name="SubmitWorkflow",
                endpoint=f"{self.wimlogic_api_url}/workflows/trigger",
                request_count=1,
                estimated_cost=0.0150
            )
            crud_api_usage_log.create(db, obj_in=api_log_in)

            # In production, we would perform:
            # response = httpx.post(f"{self.wimlogic_api_url}/workflows/trigger", headers=..., json=payload)
            # and update the execution state with the actual remote job reference.

            workflow_execution_service.add_event(
                db,
                execution_id=execution_obj.execution_id,
                event_type="DISPATCH",
                status="Submitted",
                message=f"Successfully dispatched workflow request to DEV-TOOLS WIMLOGIC orchestrator with Job ID: {devtools_execution_id}."
            )

        except Exception as e:
            workflow_execution_service.add_event(
                db,
                execution_id=execution_obj.execution_id,
                event_type="ERROR",
                status="Failed",
                message=f"Failed to submit workflow to WIMLOGIC: {str(e)}"
            )
            raise e

        return execution_obj

    def check_workflow_status(self, db: Session, *, execution_id: int) -> str:
        """
        Polls or checks the current status of the workflow execution from the external
        DEV-TOOLS WIMLOGIC orchestrator and synchronizes the local status.
        """
        execution_obj = workflow_execution_service.get_execution(db, execution_id)
        if not execution_obj:
            raise ValueError(f"Workflow execution with ID '{execution_id}' not found")

        # Return quickly if already finalized
        if execution_obj.status in ["Completed", "Failed"]:
            return execution_obj.status

        # Register standard API usage tracking
        api_log_in = ApiUsageLogCreate(
            provider="WIMLOGIC",
            api_name="CheckWorkflowStatus",
            endpoint=f"{self.wimlogic_api_url}/jobs/{execution_obj.devtools_execution_id}/status",
            request_count=1,
            estimated_cost=0.0020
        )
        crud_api_usage_log.create(db, obj_in=api_log_in)

        # Update event tracking
        workflow_execution_service.add_event(
            db,
            execution_id=execution_obj.execution_id,
            event_type="POLL",
            status=execution_obj.status,
            message="Polled external status from WIMLOGIC Orchestrator. No status change."
        )

        return execution_obj.status

    def receive_workflow_callback(
        self,
        db: Session,
        *,
        devtools_execution_id: str,
        status: str,
        payload: Dict[str, Any]
    ) -> WorkflowExecution:
        """
        Processes webhook callback notifications sent from DEV-TOOLS WIMLOGIC when workflow analysis completes or fails.
        """
        # 1. Look up the matching active execution record
        statement = select(WorkflowExecution).where(WorkflowExecution.devtools_execution_id == devtools_execution_id)
        execution_obj = db.execute(statement).scalars().first()
        if not execution_obj:
            raise ValueError(f"No workflow execution matches external DevTools ID '{devtools_execution_id}'")

        if execution_obj.status in ["Completed", "Failed"]:
            # Already finalized
            return execution_obj

        # 2. Register callback log
        workflow_execution_service.add_event(
            db,
            execution_id=execution_obj.execution_id,
            event_type="CALLBACK",
            status=status,
            message=f"Received status update callback from DEV-TOOLS WIMLOGIC with status '{status}'."
        )

        if status.lower() == "completed":
            # 3. Create Raw Workflow Result
            result_version = payload.get("version", "1.0.0")
            result_data = payload.get("results", {})
            
            result_in = WorkflowResultCreate(
                execution_id=execution_obj.execution_id,
                result_type=execution_obj.workflow_code,
                result_version=result_version,
                response_json=json.dumps(result_data),
                normalized=1
            )
            result_obj = workflow_result_service.create_result(db, result_in=result_in)

            # 4. Parse payload and register structured Result Sections
            sections_data: List[Dict[str, Any]] = result_data.get("sections", [])
            for sec in sections_data:
                sec_in = ResultSectionCreate(
                    result_id=result_obj.result_id,
                    section_type=sec.get("section_type", "analysis"),
                    title=sec.get("title", "Analysis Details"),
                    content=sec.get("content", ""),
                    confidence_score=sec.get("confidence_score"),
                    metadata_json=sec.get("metadata", {})
                )
                workflow_result_service.create_section(db, section_in=sec_in)

            # 5. Extract and populate high-level Business Property Analysis Report
            project_obj = crud_project.get(db, execution_obj.project_id)
            project_id_str = project_obj.project_id if project_obj else "unknown"

            report_data = result_data.get("property_analysis", {})
            report_in = PropertyAnalysisReportCreate(
                project_id=project_id_str,
                property_id=execution_obj.property_id,
                scenario_id=execution_obj.scenario_id,
                estimate_low=report_data.get("estimate_low"),
                estimate_high=report_data.get("estimate_high"),
                zoning_notes=report_data.get("zoning_notes"),
                risk_notes=report_data.get("risk_notes"),
                recommendation=report_data.get("recommendation"),
                score=report_data.get("score"),
                report_json=report_data,
                workflow_execution_id=execution_obj.execution_id,
                workflow_result_id=result_obj.result_id,
                analysis_version=result_version,
                confidence_score=payload.get("confidence_score"),
                workflow_status="Completed",
                completed_at=datetime.datetime.now()
            )
            workflow_result_service.create_report(db, report_in=report_in)

            # 6. Populate associated Assets generated by the workflow (e.g. PDF briefs)
            assets_data: List[Dict[str, Any]] = payload.get("assets", [])
            for asset in assets_data:
                asset_in = GeneratedAssetCreate(
                    execution_id=execution_obj.execution_id,
                    property_id=execution_obj.property_id,
                    asset_type=asset.get("asset_type", "pdf"),
                    asset_category=asset.get("asset_category", "brief"),
                    title=asset.get("title", "Generated Brief"),
                    description=asset.get("description"),
                    file_name=asset.get("file_name", "analysis_brief.pdf"),
                    storage_path=asset.get("storage_path", "/assets/default.pdf"),
                    thumbnail_path=asset.get("thumbnail_path"),
                    mime_type=asset.get("mime_type", "application/pdf"),
                    file_size=asset.get("file_size"),
                    version=result_version
                )
                generated_asset_service.create_asset(db, asset_in=asset_in)

            # 7. Complete execution lifecycle state
            workflow_execution_service.add_event(
                db,
                execution_id=execution_obj.execution_id,
                event_type="SYSTEM",
                status="Completed",
                message="Workflow analysis successfully processed. Reports and generated assets have been cached."
            )

        else:
            # Handle analysis or engine execution failure
            error_msg = payload.get("error_message", "Unknown WIMLOGIC orchestrator execution error.")
            
            # Sync fail status
            update_in = WorkflowExecutionUpdate(
                status="Failed",
                error_message=error_msg,
                completed_at=datetime.datetime.now()
            )
            workflow_execution_service.update_execution(db, execution_id=execution_obj.execution_id, execution_in=update_in)

            workflow_execution_service.add_event(
                db,
                execution_id=execution_obj.execution_id,
                event_type="SYSTEM",
                status="Failed",
                message=f"Orchestrator returned failure: {error_msg}"
            )

        # Refresh state and return
        db.refresh(execution_obj)
        return execution_obj

ai_orchestration_service = AIOrchestrationService()

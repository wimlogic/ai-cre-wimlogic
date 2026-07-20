from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class WorkflowExecutionBase(BaseModel):
    execution_number: str
    project_id: int
    property_id: int
    scenario_id: Optional[int] = None
    workflow_code: str
    workflow_version: Optional[str] = None
    devtools_execution_id: Optional[str] = None
    status: str = "Pending"
    priority: str = "Normal"
    requested_by: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    result_sync_error: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

class WorkflowExecutionCreate(WorkflowExecutionBase):
    pass

class WorkflowExecutionUpdate(BaseModel):
    execution_number: Optional[str] = None
    project_id: Optional[int] = None
    property_id: Optional[int] = None
    scenario_id: Optional[int] = None
    workflow_code: Optional[str] = None
    workflow_version: Optional[str] = None
    devtools_execution_id: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    requested_by: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: Optional[int] = None
    error_message: Optional[str] = None
    result_sync_error: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

class WorkflowExecutionRead(WorkflowExecutionBase):
    execution_id: int
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkflowExecutionResponse(WorkflowExecutionRead):
    pass

class WorkflowExecutionListResponse(BaseModel):
    count: int
    items: List[WorkflowExecutionRead]

    model_config = ConfigDict(from_attributes=True)

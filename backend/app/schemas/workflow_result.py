from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class WorkflowResultBase(BaseModel):
    execution_id: int
    result_type: str
    result_version: Optional[str] = None
    response_json: Optional[str] = None
    normalized: int = 1

class WorkflowResultCreate(WorkflowResultBase):
    pass

class WorkflowResultUpdate(BaseModel):
    execution_id: Optional[int] = None
    result_type: Optional[str] = None
    result_version: Optional[str] = None
    response_json: Optional[str] = None
    normalized: Optional[int] = None

class WorkflowResultRead(WorkflowResultBase):
    result_id: int
    received_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkflowResultResponse(WorkflowResultRead):
    pass

class WorkflowResultListResponse(BaseModel):
    count: int
    items: List[WorkflowResultRead]

    model_config = ConfigDict(from_attributes=True)

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class WorkflowEventBase(BaseModel):
    execution_id: int
    event_type: str
    status: str
    message: Optional[str] = None

class WorkflowEventCreate(WorkflowEventBase):
    pass

class WorkflowEventUpdate(BaseModel):
    execution_id: Optional[int] = None
    event_type: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None

class WorkflowEventRead(WorkflowEventBase):
    event_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkflowEventResponse(WorkflowEventRead):
    pass

class WorkflowEventListResponse(BaseModel):
    count: int
    items: List[WorkflowEventRead]

    model_config = ConfigDict(from_attributes=True)

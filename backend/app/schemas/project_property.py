from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class ProjectPropertyBase(BaseModel):
    project_id: str
    property_id: int
    scan_id: Optional[str] = None
    role: Optional[str] = None
    selected: int = 0

class ProjectPropertyCreate(ProjectPropertyBase):
    pass

class ProjectPropertyUpdate(BaseModel):
    project_id: Optional[str] = None
    property_id: Optional[int] = None
    scan_id: Optional[str] = None
    role: Optional[str] = None
    selected: Optional[int] = None

class ProjectPropertyRead(ProjectPropertyBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProjectPropertyResponse(ProjectPropertyRead):
    pass

class ProjectPropertyListResponse(BaseModel):
    count: int
    items: List[ProjectPropertyRead]

    model_config = ConfigDict(from_attributes=True)

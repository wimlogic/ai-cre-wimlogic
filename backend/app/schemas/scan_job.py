from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class ScanJobBase(BaseModel):
    scan_id: str
    project_id: str
    project_name: str
    main_street: str
    beginning_address: str
    ending_address: str
    side_selection: str
    status: str = "created"
    found_count: int = 0
    notes: Optional[str] = None
    scan_source: Optional[str] = None

class ScanJobCreate(ScanJobBase):
    pass

class ScanJobUpdate(BaseModel):
    scan_id: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    main_street: Optional[str] = None
    beginning_address: Optional[str] = None
    ending_address: Optional[str] = None
    side_selection: Optional[str] = None
    status: Optional[str] = None
    found_count: Optional[int] = None
    notes: Optional[str] = None
    scan_source: Optional[str] = None

class ScanJobRead(ScanJobBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ScanJobResponse(ScanJobRead):
    pass

class ScanJobListResponse(BaseModel):
    count: int
    items: List[ScanJobRead]

    model_config = ConfigDict(from_attributes=True)

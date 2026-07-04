from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class ScanBase(BaseModel):
    scan_uid: str
    city: Optional[str] = None
    state: Optional[str] = None
    main_street: Optional[str] = None
    start_address: Optional[str] = None
    end_address: Optional[str] = None
    side: str
    scan_mode: str
    status: str = "pending"
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    scan_source: Optional[str] = None

class ScanCreate(ScanBase):
    pass

class ScanUpdate(BaseModel):
    scan_uid: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    main_street: Optional[str] = None
    start_address: Optional[str] = None
    end_address: Optional[str] = None
    side: Optional[str] = None
    scan_mode: Optional[str] = None
    status: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    scan_source: Optional[str] = None

class ScanRead(ScanBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ScanResponse(ScanRead):
    pass

class ScanListResponse(BaseModel):
    count: int
    items: List[ScanRead]

    model_config = ConfigDict(from_attributes=True)

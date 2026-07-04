from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class ScanPropertyBase(BaseModel):
    scan_id: int
    property_id: int
    scan_order: Optional[int] = None
    side_of_street: Optional[str] = None
    frontage_street: Optional[str] = None
    included_reason: Optional[str] = None

class ScanPropertyCreate(ScanPropertyBase):
    pass

class ScanPropertyUpdate(BaseModel):
    scan_id: Optional[int] = None
    property_id: Optional[int] = None
    scan_order: Optional[int] = None
    side_of_street: Optional[str] = None
    frontage_street: Optional[str] = None
    included_reason: Optional[str] = None

class ScanPropertyRead(ScanPropertyBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class ScanPropertyResponse(ScanPropertyRead):
    pass

class ScanPropertyListResponse(BaseModel):
    count: int
    items: List[ScanPropertyRead]

    model_config = ConfigDict(from_attributes=True)


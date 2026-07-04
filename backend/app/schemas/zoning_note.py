from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class ZoningNoteBase(BaseModel):
    property_id: int
    zoning_code: Optional[str] = None
    allowed_use_summary: Optional[str] = None
    conditional_use_notes: Optional[str] = None
    parking_notes: Optional[str] = None
    entitlement_risk: str = "medium"
    source_url: Optional[str] = None

class ZoningNoteCreate(ZoningNoteBase):
    pass

class ZoningNoteUpdate(BaseModel):
    property_id: Optional[int] = None
    zoning_code: Optional[str] = None
    allowed_use_summary: Optional[str] = None
    conditional_use_notes: Optional[str] = None
    parking_notes: Optional[str] = None
    entitlement_risk: Optional[str] = None
    source_url: Optional[str] = None

class ZoningNoteRead(ZoningNoteBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ZoningNoteResponse(ZoningNoteRead):
    pass

class ZoningNoteListResponse(BaseModel):
    count: int
    items: List[ZoningNoteRead]

    model_config = ConfigDict(from_attributes=True)

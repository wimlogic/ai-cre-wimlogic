from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class ResultSectionBase(BaseModel):
    result_id: int
    section_type: str
    display_order: int = 0
    title: Optional[str] = None
    content: Optional[str] = None
    confidence_score: Optional[float] = None

class ResultSectionCreate(ResultSectionBase):
    pass

class ResultSectionUpdate(BaseModel):
    result_id: Optional[int] = None
    section_type: Optional[str] = None
    display_order: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None
    confidence_score: Optional[float] = None

class ResultSectionRead(ResultSectionBase):
    section_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ResultSectionResponse(ResultSectionRead):
    pass

class ResultSectionListResponse(BaseModel):
    count: int
    items: List[ResultSectionRead]

    model_config = ConfigDict(from_attributes=True)


from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class ApiUsageLogBase(BaseModel):
    provider: Optional[str] = None
    api_name: Optional[str] = None
    endpoint: Optional[str] = None
    request_count: Optional[int] = 1
    estimated_cost: Optional[float] = None

class ApiUsageLogCreate(ApiUsageLogBase):
    pass

class ApiUsageLogUpdate(BaseModel):
    provider: Optional[str] = None
    api_name: Optional[str] = None
    endpoint: Optional[str] = None
    request_count: Optional[int] = None
    estimated_cost: Optional[float] = None

class ApiUsageLogRead(ApiUsageLogBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ApiUsageLogResponse(ApiUsageLogRead):
    pass

class ApiUsageLogListResponse(BaseModel):
    count: int
    items: List[ApiUsageLogRead]

    model_config = ConfigDict(from_attributes=True)

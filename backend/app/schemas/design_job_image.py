from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

class DesignJobImageCreate(BaseModel):
    design_job_id: int
    property_image_id: int
    input_role: str = "primary"  # primary, supporting, reference
    image_knowledge_snapshot_json: Optional[Dict[str, Any]] = None
    display_order: int = 0

class DesignJobImageRead(DesignJobImageCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

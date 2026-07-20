from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, field_validator

class ApprovedDesignBaselineApproveRequest(BaseModel):
    """
    The client supplies only the two facts a human approver actually
    decides: which generated version is being approved, and which design
    scope it belongs to. Every other baseline field - project_id,
    property_id, design_job_id, tool_id, tool_code, design_type,
    tool_options_json, effective_context_json, submitted_payload_json - is
    derived and snapshotted by the service from the approved Image Version
    and its Design Job. None of those are accepted from the client here.
    """
    image_version_id: int
    design_scope: str

    @field_validator("design_scope")
    @classmethod
    def _design_scope_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("design_scope must not be empty")
        return v

class ApprovedDesignBaselineRead(BaseModel):
    id: int
    baseline_uid: str
    project_id: str
    property_id: int
    design_job_id: int
    image_version_id: int
    tool_id: int
    tool_code: str
    design_type: str
    design_scope: str
    tool_options_json: Optional[Dict[str, Any]] = None
    effective_context_json: Optional[Dict[str, Any]] = None
    submitted_payload_json: Optional[Dict[str, Any]] = None
    status: str  # active, superseded
    # Database GENERATED ALWAYS ... STORED column - read-only, never
    # supplied by the client and never assigned by service/CRUD code.
    active_scope_key: Optional[str] = None
    approved_by: Optional[int] = None
    approved_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ApprovedDesignBaselineResponse(ApprovedDesignBaselineRead):
    pass

class ApprovedDesignBaselineListResponse(BaseModel):
    count: int
    items: List[ApprovedDesignBaselineRead]

    model_config = ConfigDict(from_attributes=True)

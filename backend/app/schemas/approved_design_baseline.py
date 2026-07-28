from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, field_validator

class ApprovedDesignBaselineApproveRequest(BaseModel):
    """
    The client supplies only the one fact a human approver actually
    decides: which generated version is being approved. Every other
    baseline field - project_id, property_id, design_job_id, tool_id,
    tool_code, design_type, tool_options_json, effective_context_json,
    submitted_payload_json - is derived and snapshotted by the service
    from the approved Image Version and its Design Job. None of those
    are accepted from the client here.

    design_scope is optional and, for AIHOME Phase 1, is always derived
    server-side (design_result_service._resolve_design_scope() - the
    Design Job's primary selected image's own image_role, e.g.
    "kitchen"). This is a documented TEMPORARY Phase 1 implementation,
    not a permanent design: a future phase may let an approver supply an
    explicit design_scope override, at which point this field would stop
    being ignored. It is accepted here now only so the schema doesn't
    need a breaking change later - the service does not currently read
    it even when supplied.
    """
    image_version_id: int
    design_scope: Optional[str] = None

    @field_validator("design_scope")
    @classmethod
    def _design_scope_non_empty_if_supplied(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("design_scope, if supplied, must not be empty")
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

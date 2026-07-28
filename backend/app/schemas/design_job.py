from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

class DesignJobCreate(BaseModel):
    """
    Creates the persistent draft business workspace only. Per the locked
    lifecycle (CREATE -> CONFIGURE -> SUBMIT -> RETRY), this deliberately
    does NOT accept selected images, tool options, effective context,
    submitted payload, or any workflow execution reference - none of those
    exist yet at creation time.
    """
    project_id: str
    property_id: int
    tool_id: int


class DesignJobConfigureImageItem(BaseModel):
    """
    AIHOME Design Studio V2 - Image Workspace Evolution. Exactly one of
    property_image_id / source_image_version_id must be set: an original
    Property Image, or a prior DesignImageVersion (a permanent Design
    Asset AIHOME owns, not a transient workflow output) used as a
    reference for this new, independent Design Job. The user explicitly
    selects both kinds from the same Image Workspace picker; nothing is
    automatically carried over from a prior job.

    Uses model_validator(mode="after"), not field_validator - both
    fields default to None, and Pydantic v2 does not run a plain
    field_validator when a field keeps its default value, which would
    silently let "neither set" through undetected (confirmed by testing
    this exact failure mode before switching approaches).
    """
    property_image_id: Optional[int] = None
    source_image_version_id: Optional[int] = None
    input_role: str = "primary"  # primary, supporting, reference

    @model_validator(mode="after")
    def _exactly_one_source(self) -> "DesignJobConfigureImageItem":
        if (self.property_image_id is None) == (self.source_image_version_id is None):
            raise ValueError(
                "Exactly one of property_image_id or source_image_version_id must be set, not both and not neither."
            )
        return self


class DesignJobConfigureImagesRequest(BaseModel):
    """
    Replaces the draft's selected-image set. Callable repeatedly while the
    Design Job is still status='draft'. Ownership (images must belong to
    the Job's property) is a service-layer check, not enforced here.
    """
    images: List[DesignJobConfigureImageItem]

    @field_validator("images")
    @classmethod
    def _images_non_empty_list(cls, v: List[DesignJobConfigureImageItem]) -> List[DesignJobConfigureImageItem]:
        if v is None:
            raise ValueError("images must be a list")
        return v


class DesignJobConfigureOptionsRequest(BaseModel):
    """
    Overwrites the draft's tool_options_json in place. Callable repeatedly
    while status='draft'. Validation against the Tool's actual option
    definitions (cre_design_tool_options) is a service-layer responsibility,
    not enforced here - this schema only validates structural shape.

    job_prompt / job_constraints (Knowledge Inheritance Engine Phase 1.2A):
    job-wide instructions, distinct in scope from per-image ai_prompt/
    constraints on cre_property_images - both are aggregated into
    effective_context, neither overrides the other. Optional and
    independently settable from tool_options; omitting them on a given
    call leaves the job's current values unchanged (only tool_options is
    unconditionally overwritten, matching this endpoint's existing
    "overwrites in place" contract for that one field).
    """
    tool_options: Dict[str, Any]
    job_prompt: Optional[str] = None
    job_constraints: Optional[str] = None


class DesignJobRead(BaseModel):
    """
    Maps cre_design_jobs exactly as approved in Checkpoint 1. Note:
    submitted_at, completed_at, and error_message are NOT included here -
    see CHECKPOINT 2 issue report, section 9. Those three fields do not
    exist as columns on the approved cre_design_jobs table or the
    Checkpoint-1-approved DesignJob ORM model; adding them here would
    describe a schema that isn't the one currently migrated.
    """
    id: int
    job_number: str
    project_id: str
    property_id: int
    tool_id: int
    tool_code: str
    design_type: str
    workflow_code: str
    tool_options_json: Optional[Dict[str, Any]] = None
    effective_context_json: Optional[Dict[str, Any]] = None
    submitted_payload_json: Optional[Dict[str, Any]] = None
    job_prompt: Optional[str] = None
    job_constraints: Optional[str] = None
    status: str
    requested_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DesignJobResponse(DesignJobRead):
    pass


class DesignJobListResponse(BaseModel):
    count: int
    items: List[DesignJobRead]

    model_config = ConfigDict(from_attributes=True)


class DesignJobSubmitResponse(BaseModel):
    """
    Returned by POST /jobs/{id}/submit. No request body schema exists for
    submit - submission always acts on the job's current draft
    configuration; there is nothing left for a caller to pass in.
    """
    design_job_id: int
    attempt_number: int
    workflow_execution_id: int
    devtools_execution_id: Optional[str] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class DesignJobRetryResponse(DesignJobSubmitResponse):
    """
    Same business response shape as submit. No request body schema exists
    for retry either - retry reuses the existing frozen
    submitted_payload_json and cannot accept new configuration by
    definition (see the locked Retry Payload Semantics determination).
    """
    pass

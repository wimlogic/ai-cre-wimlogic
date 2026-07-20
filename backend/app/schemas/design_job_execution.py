from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict

class DesignJobExecutionRead(BaseModel):
    """
    Read-only through the API - created only by the Design Job submit/retry
    business services. Note: attempt_status and updated_at are NOT included
    here - see CHECKPOINT 2 issue report, section 9. Neither exists as a
    column on the approved cre_design_job_executions table or the
    Checkpoint-1-approved DesignJobExecution ORM model; this table is
    deliberately pure attempt bookkeeping (attempt_number + is_current),
    per the locked Design Job / Execution architecture. Attempt-level
    status is available via the joined cre_workflow_executions row
    (workflow_execution_id), not duplicated onto this table.
    """
    id: int
    design_job_id: int
    workflow_execution_id: int
    attempt_number: int
    is_current: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DesignJobExecutionListResponse(BaseModel):
    count: int
    items: List[DesignJobExecutionRead]

    model_config = ConfigDict(from_attributes=True)

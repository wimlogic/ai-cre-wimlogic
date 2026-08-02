# PATCH INSTRUCTIONS — app/crud/design_image_version.py

I do not have a verified copy of this file either (same reason as the
model - never modified in any prior delivery). This is a small,
mechanical extension, following the EXACT pattern already used when
`workflow_result_id` was added as a filter to the equivalent
PropertyAnalysisReport CRUD in an earlier phase of this project.

Find `get_multi()`'s signature and body. It currently accepts
`design_job_id`, `property_id`, `status` as optional filters (confirmed
via the real, recovered router file that calls it). Add one more
parameter, following the exact same shape as the others:

```python
def get_multi(
    self, db: Session, *, skip: int = 0, limit: int = 100,
    design_job_id: Optional[int] = None,
    property_id: Optional[int] = None,
    status: Optional[str] = None,
    workflow_execution_id: Optional[int] = None,   # <-- new
) -> Tuple[List[DesignImageVersion], int]:
    query = select(DesignImageVersion)
    if design_job_id:
        query = query.where(DesignImageVersion.design_job_id == design_job_id)
    if property_id:
        query = query.where(DesignImageVersion.property_id == property_id)
    if status:
        query = query.where(DesignImageVersion.status == status)
    if workflow_execution_id:                       # <-- new
        query = query.where(DesignImageVersion.workflow_execution_id == workflow_execution_id)
    ...
```

`DesignImageVersion.workflow_execution_id` already exists as a column
(it's populated by `create_design_image_version()` on every row, always
has been) - this patch only exposes it as a query filter; no model or
migration change is needed for this specific piece.

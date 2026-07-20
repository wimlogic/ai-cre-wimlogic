from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.design_job import DesignJob
from app.schemas.design_job import DesignJobCreate

class CRUDDesignJob:
    def get(self, db: Session, id: int) -> Optional[DesignJob]:
        return db.get(DesignJob, id)

    def lock_for_update(self, db: Session, id: int) -> Optional[DesignJob]:
        """
        Locks the Design Job row with SELECT ... FOR UPDATE, establishing
        the Design Job as the serialization boundary for CONFIGURE
        operations (set_images, set_tool_options) and, per the locked
        Checkpoint 7 contract, SUBMIT as well - both must serialize on
        this same row so a Configure request can never commit after a
        Submit has already frozen the Job's configuration. Pure DB access
        only - does not commit, does not roll back, and contains no
        lifecycle business logic; the calling service owns the
        surrounding transaction. Returns None if the Design Job does not
        exist.
        """
        statement = select(DesignJob).where(DesignJob.id == id).with_for_update()
        return db.execute(statement).scalars().first()

    def get_by_job_number(self, db: Session, job_number: str) -> Optional[DesignJob]:
        statement = select(DesignJob).where(DesignJob.job_number == job_number)
        return db.execute(statement).scalars().first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, property_id: Optional[int] = None, project_id: Optional[str] = None, tool_id: Optional[int] = None, status: Optional[str] = None
    ) -> Tuple[List[DesignJob], int]:
        query = select(DesignJob)

        if property_id is not None:
            query = query.where(DesignJob.property_id == property_id)
        if project_id:
            query = query.where(DesignJob.project_id == project_id)
        if tool_id is not None:
            query = query.where(DesignJob.tool_id == tool_id)
        if status:
            query = query.where(DesignJob.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()

        statement = query.order_by(DesignJob.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()

        return list(results), total_count

    def create(
        self, db: Session, *, obj_in: DesignJobCreate, job_number: str, tool_code: str, design_type: str, workflow_code: str, commit: bool = True
    ) -> DesignJob:
        """
        DesignJobCreate (Checkpoint 2) intentionally carries only
        project_id/property_id/tool_id - it is the client-facing draft
        creation contract. job_number, tool_code, design_type, and
        workflow_code are NOT client-supplied: they are resolved by the
        service layer (job_number generation, Tool lookup) and passed in
        here as separate keyword arguments so this method can still
        construct a complete, NOT-NULL-satisfying row. status defaults to
        'draft' via the ORM model's own column default and is not set here.

        commit=True (default): standalone use - commits and refreshes.
        commit=False: participates in a service-owned transaction - only
        flushes (so db_obj.id is populated) and does NOT commit or roll
        back. The calling service owns commit/rollback.
        """
        db_obj = DesignJob(
            **obj_in.model_dump(),
            job_number=job_number,
            tool_code=tool_code,
            design_type=design_type,
            workflow_code=workflow_code,
        )
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def update(self, db: Session, *, db_obj: DesignJob, obj_in: Dict[str, Any], commit: bool = True) -> DesignJob:
        """
        No DesignJobUpdate Pydantic schema exists (approved Checkpoint 2
        decision - configuration happens only via the narrow Configure
        Images/Options request schemas, and the Stage C freeze fields are
        service-computed, not client-supplied). This method accepts a
        plain dict of already-validated fields from the service layer
        (e.g. tool_options_json, effective_context_json,
        submitted_payload_json, status) rather than a schema object.
        """
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

design_job = CRUDDesignJob()

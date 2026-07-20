from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.design_job_execution import DesignJobExecution

class CRUDDesignJobExecution:
    def get(self, db: Session, id: int) -> Optional[DesignJobExecution]:
        return db.get(DesignJobExecution, id)

    def get_current(self, db: Session, *, design_job_id: int) -> Optional[DesignJobExecution]:
        statement = select(DesignJobExecution).where(
            DesignJobExecution.design_job_id == design_job_id,
            DesignJobExecution.is_current == 1,
        )
        return db.execute(statement).scalars().first()

    def get_by_workflow_execution_id(self, db: Session, *, workflow_execution_id: int) -> Optional[DesignJobExecution]:
        statement = select(DesignJobExecution).where(DesignJobExecution.workflow_execution_id == workflow_execution_id)
        return db.execute(statement).scalars().first()

    def get_max_attempt_number(self, db: Session, *, design_job_id: int) -> int:
        statement = select(func.max(DesignJobExecution.attempt_number)).where(DesignJobExecution.design_job_id == design_job_id)
        result = db.execute(statement).scalar_one_or_none()
        return result or 0

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, design_job_id: Optional[int] = None
    ) -> Tuple[List[DesignJobExecution], int]:
        query = select(DesignJobExecution)

        if design_job_id is not None:
            query = query.where(DesignJobExecution.design_job_id == design_job_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()

        statement = query.order_by(DesignJobExecution.attempt_number.asc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()

        return list(results), total_count

    def create(self, db: Session, *, obj_in: Dict[str, Any], commit: bool = True) -> DesignJobExecution:
        """
        No public Create schema exists for this entity (Checkpoint 2:
        read-only through the API, created only by Design Job submit/retry
        business services). Expected keys: design_job_id,
        workflow_execution_id, attempt_number, is_current.

        This method is a required participant in the Design Job Execution
        Attempt transaction (flip prior is_current -> 0, then insert the
        new current attempt row) - commit=False lets both writes share one
        service-owned transaction. Use commit=False here paired with
        update(..., commit=False) on the prior attempt.
        """
        db_obj = DesignJobExecution(**obj_in)
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def update(self, db: Session, *, db_obj: DesignJobExecution, obj_in: Dict[str, Any], commit: bool = True) -> DesignJobExecution:
        """
        Used to flip is_current when a new attempt becomes current. No
        public Update schema exists for this entity, for the same reason
        as create() above.
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

design_job_execution = CRUDDesignJobExecution()

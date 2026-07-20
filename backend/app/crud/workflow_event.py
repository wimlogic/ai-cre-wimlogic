from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.workflow_event import WorkflowEvent
from app.schemas.workflow_event import WorkflowEventCreate, WorkflowEventUpdate

class CRUDWorkflowEvent:
    def get(self, db: Session, event_id: int) -> Optional[WorkflowEvent]:
        return db.get(WorkflowEvent, event_id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, execution_id: Optional[int] = None, status: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[WorkflowEvent], int]:
        query = select(WorkflowEvent)
        
        # Apply filters
        if execution_id:
            query = query.where(WorkflowEvent.execution_id == execution_id)
        if status:
            query = query.where(WorkflowEvent.status == status)
        if search:
            query = query.where(
                or_(
                    WorkflowEvent.event_type.ilike(f"%{search}%"),
                    WorkflowEvent.message.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(WorkflowEvent.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: WorkflowEventCreate, commit: bool = True) -> WorkflowEvent:
        """
        commit=True (default, unchanged): standalone use - commits and
        refreshes, exactly as before this change.
        commit=False: participates in a service-owned transaction (Design
        Studio Phase 1 local attempt registration, Checkpoint 8) - only
        flushes, does not commit or roll back.
        """
        db_obj = WorkflowEvent(**obj_in.model_dump())
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def update(self, db: Session, *, db_obj: WorkflowEvent, obj_in: WorkflowEventUpdate) -> WorkflowEvent:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, event_id: int) -> Optional[WorkflowEvent]:
        obj = db.get(WorkflowEvent, event_id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

workflow_event = CRUDWorkflowEvent()

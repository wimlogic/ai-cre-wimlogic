from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.workflow_execution import WorkflowExecution
from app.schemas.workflow_execution import WorkflowExecutionCreate, WorkflowExecutionUpdate

class CRUDWorkflowExecution:
    def get(self, db: Session, execution_id: int) -> Optional[WorkflowExecution]:
        return db.get(WorkflowExecution, execution_id)

    def get_by_execution_number(self, db: Session, execution_number: str) -> Optional[WorkflowExecution]:
        statement = select(WorkflowExecution).where(WorkflowExecution.execution_number == execution_number)
        return db.execute(statement).scalars().first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, project_id: Optional[int] = None, property_id: Optional[int] = None, status: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[WorkflowExecution], int]:
        query = select(WorkflowExecution)
        
        # Apply filters
        if project_id is not None:
            query = query.where(WorkflowExecution.project_id == project_id)
        if property_id is not None:
            query = query.where(WorkflowExecution.property_id == property_id)
        if status:
            query = query.where(WorkflowExecution.status == status)
        if search:
            query = query.where(
                or_(
                    WorkflowExecution.execution_number.ilike(f"%{search}%"),
                    WorkflowExecution.workflow_code.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(WorkflowExecution.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: WorkflowExecutionCreate) -> WorkflowExecution:
        db_obj = WorkflowExecution(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: WorkflowExecution, obj_in: WorkflowExecutionUpdate) -> WorkflowExecution:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, execution_id: int) -> Optional[WorkflowExecution]:
        obj = db.get(WorkflowExecution, execution_id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

workflow_execution = CRUDWorkflowExecution()

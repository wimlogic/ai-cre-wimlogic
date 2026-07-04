from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.workflow_result import WorkflowResult
from app.schemas.workflow_result import WorkflowResultCreate, WorkflowResultUpdate

class CRUDWorkflowResult:
    def get(self, db: Session, result_id: int) -> Optional[WorkflowResult]:
        return db.get(WorkflowResult, result_id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, execution_id: Optional[int] = None, search: Optional[str] = None
    ) -> Tuple[List[WorkflowResult], int]:
        query = select(WorkflowResult)
        
        # Apply filters
        if execution_id is not None:
            query = query.where(WorkflowResult.execution_id == execution_id)
        if search:
            query = query.where(
                or_(
                    WorkflowResult.result_type.ilike(f"%{search}%"),
                    WorkflowResult.response_json.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(WorkflowResult.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: WorkflowResultCreate) -> WorkflowResult:
        db_obj = WorkflowResult(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: WorkflowResult, obj_in: WorkflowResultUpdate) -> WorkflowResult:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, result_id: int) -> Optional[WorkflowResult]:
        obj = db.get(WorkflowResult, result_id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

workflow_result = CRUDWorkflowResult()

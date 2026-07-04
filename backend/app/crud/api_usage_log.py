from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.api_usage_log import ApiUsageLog
from app.schemas.api_usage_log import ApiUsageLogCreate, ApiUsageLogUpdate

class CRUDApiUsageLog:
    def get(self, db: Session, id: int) -> Optional[ApiUsageLog]:
        return db.get(ApiUsageLog, id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, provider: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[ApiUsageLog], int]:
        query = select(ApiUsageLog)
        
        # Apply filters
        if provider:
            query = query.where(ApiUsageLog.provider == provider)
        if search:
            query = query.where(
                or_(
                    ApiUsageLog.api_name.ilike(f"%{search}%"),
                    ApiUsageLog.endpoint.ilike(f"%{search}%"),
                    ApiUsageLog.provider.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(ApiUsageLog.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: ApiUsageLogCreate) -> ApiUsageLog:
        db_obj = ApiUsageLog(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: ApiUsageLog, obj_in: ApiUsageLogUpdate) -> ApiUsageLog:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[ApiUsageLog]:
        obj = db.get(ApiUsageLog, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

api_usage_log = CRUDApiUsageLog()

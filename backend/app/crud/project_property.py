from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.project_property import ProjectProperty
from app.schemas.project_property import ProjectPropertyCreate, ProjectPropertyUpdate

class CRUDProjectProperty:
    def get(self, db: Session, id: int) -> Optional[ProjectProperty]:
        return db.get(ProjectProperty, id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, project_id: Optional[str] = None, property_id: Optional[int] = None, scan_id: Optional[str] = None
    ) -> Tuple[List[ProjectProperty], int]:
        query = select(ProjectProperty)
        
        # Apply filters
        if project_id:
            query = query.where(ProjectProperty.project_id == project_id)
        if property_id:
            query = query.where(ProjectProperty.property_id == property_id)
        if scan_id:
            query = query.where(ProjectProperty.scan_id == scan_id)
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(ProjectProperty.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: ProjectPropertyCreate) -> ProjectProperty:
        db_obj = ProjectProperty(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: ProjectProperty, obj_in: ProjectPropertyUpdate) -> ProjectProperty:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[ProjectProperty]:
        obj = db.get(ProjectProperty, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

project_property = CRUDProjectProperty()

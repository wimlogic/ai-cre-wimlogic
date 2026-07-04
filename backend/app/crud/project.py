from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate

class CRUDProject:
    def get(self, db: Session, id: int) -> Optional[Project]:
        return db.get(Project, id)

    def get_by_project_id(self, db: Session, project_id: str) -> Optional[Project]:
        statement = select(Project).where(Project.project_id == project_id)
        return db.execute(statement).scalars().first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, status: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[Project], int]:
        query = select(Project)
        
        # Apply filters
        if status:
            query = query.where(Project.status == status)
        if search:
            query = query.where(
                or_(
                    Project.project_name.ilike(f"%{search}%"),
                    Project.description.ilike(f"%{search}%"),
                    Project.project_id.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: ProjectCreate) -> Project:
        db_obj = Project(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Project, obj_in: ProjectUpdate) -> Project:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[Project]:
        obj = db.get(Project, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

project = CRUDProject()

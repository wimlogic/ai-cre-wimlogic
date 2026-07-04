from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.result_section import ResultSection
from app.schemas.result_section import ResultSectionCreate, ResultSectionUpdate

class CRUDResultSection:
    def get(self, db: Session, section_id: int) -> Optional[ResultSection]:
        return db.get(ResultSection, section_id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, result_id: Optional[int] = None, section_type: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[ResultSection], int]:
        query = select(ResultSection)
        
        # Apply filters
        if result_id:
            query = query.where(ResultSection.result_id == result_id)
        if section_type:
            query = query.where(ResultSection.section_type == section_type)
        if search:
            query = query.where(
                or_(
                    ResultSection.section_type.ilike(f"%{search}%"),
                    ResultSection.title.ilike(f"%{search}%"),
                    ResultSection.content.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(ResultSection.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: ResultSectionCreate) -> ResultSection:
        db_obj = ResultSection(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: ResultSection, obj_in: ResultSectionUpdate) -> ResultSection:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, section_id: int) -> Optional[ResultSection]:
        obj = db.get(ResultSection, section_id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

result_section = CRUDResultSection()


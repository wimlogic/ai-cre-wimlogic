from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.concept_design import ConceptDesign
from app.schemas.concept_design import ConceptDesignCreate, ConceptDesignUpdate

class CRUDConceptDesign:
    def get(self, db: Session, id: int) -> Optional[ConceptDesign]:
        return db.get(ConceptDesign, id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, project_id: Optional[str] = None, property_id: Optional[int] = None, status: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[ConceptDesign], int]:
        query = select(ConceptDesign)
        
        # Apply filters
        if project_id:
            query = query.where(ConceptDesign.project_id == project_id)
        if property_id:
            query = query.where(ConceptDesign.property_id == property_id)
        if status:
            query = query.where(ConceptDesign.status == status)
        if search:
            query = query.where(
                or_(
                    ConceptDesign.title.ilike(f"%{search}%"),
                    ConceptDesign.concept_prompt.ilike(f"%{search}%"),
                    ConceptDesign.concept_notes.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(ConceptDesign.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: ConceptDesignCreate) -> ConceptDesign:
        db_obj = ConceptDesign(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: ConceptDesign, obj_in: ConceptDesignUpdate) -> ConceptDesign:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[ConceptDesign]:
        obj = db.get(ConceptDesign, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

concept_design = CRUDConceptDesign()

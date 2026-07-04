from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.zoning_note import ZoningNote
from app.schemas.zoning_note import ZoningNoteCreate, ZoningNoteUpdate

class CRUDZoningNote:
    def get(self, db: Session, id: int) -> Optional[ZoningNote]:
        return db.get(ZoningNote, id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, property_id: Optional[int] = None, entitlement_risk: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[ZoningNote], int]:
        query = select(ZoningNote)
        
        # Apply filters
        if property_id is not None:
            query = query.where(ZoningNote.property_id == property_id)
        if entitlement_risk:
            query = query.where(ZoningNote.entitlement_risk == entitlement_risk)
        if search:
            query = query.where(
                or_(
                    ZoningNote.zoning_code.ilike(f"%{search}%"),
                    ZoningNote.allowed_use_summary.ilike(f"%{search}%"),
                    ZoningNote.conditional_use_notes.ilike(f"%{search}%"),
                    ZoningNote.parking_notes.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(ZoningNote.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: ZoningNoteCreate) -> ZoningNote:
        db_obj = ZoningNote(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: ZoningNote, obj_in: ZoningNoteUpdate) -> ZoningNote:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[ZoningNote]:
        obj = db.get(ZoningNote, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

zoning_note = CRUDZoningNote()

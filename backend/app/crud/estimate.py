from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.estimate import Estimate
from app.schemas.estimate import EstimateCreate, EstimateUpdate

class CRUDEstimate:
    def get(self, db: Session, id: int) -> Optional[Estimate]:
        return db.get(Estimate, id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, property_id: Optional[int] = None, search: Optional[str] = None
    ) -> Tuple[List[Estimate], int]:
        query = select(Estimate)
        
        # Apply filters
        if property_id:
            query = query.where(Estimate.property_id == property_id)
        if search:
            query = query.where(
                or_(
                    Estimate.scenario.ilike(f"%{search}%"),
                    Estimate.proposed_use.ilike(f"%{search}%"),
                    Estimate.assumptions.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(Estimate.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: EstimateCreate) -> Estimate:
        db_obj = Estimate(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Estimate, obj_in: EstimateUpdate) -> Estimate:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[Estimate]:
        obj = db.get(Estimate, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

estimate = CRUDEstimate()

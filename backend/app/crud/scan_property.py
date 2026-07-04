from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.scan_property import ScanProperty
from app.schemas.scan_property import ScanPropertyCreate, ScanPropertyUpdate

class CRUDScanProperty:
    def get(self, db: Session, id: int) -> Optional[ScanProperty]:
        return db.get(ScanProperty, id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, scan_id: Optional[int] = None, property_id: Optional[int] = None
    ) -> Tuple[List[ScanProperty], int]:
        query = select(ScanProperty)
        
        # Apply filters
        if scan_id is not None:
            query = query.where(ScanProperty.scan_id == scan_id)
        if property_id is not None:
            query = query.where(ScanProperty.property_id == property_id)
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(ScanProperty.id.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: ScanPropertyCreate) -> ScanProperty:
        db_obj = ScanProperty(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: ScanProperty, obj_in: ScanPropertyUpdate) -> ScanProperty:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[ScanProperty]:
        obj = db.get(ScanProperty, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

scan_property = CRUDScanProperty()


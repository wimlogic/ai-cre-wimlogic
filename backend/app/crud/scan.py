from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.scan import Scan
from app.schemas.scan import ScanCreate, ScanUpdate

class CRUDScan:
    def get(self, db: Session, id: int) -> Optional[Scan]:
        return db.get(Scan, id)

    def get_by_uid(self, db: Session, scan_uid: str) -> Optional[Scan]:
        statement = select(Scan).where(Scan.scan_uid == scan_uid)
        return db.execute(statement).scalars().first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, project_id: Optional[str] = None, status: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[Scan], int]:
        query = select(Scan)
        
        # Apply filters
        if project_id:
            query = query.where(Scan.project_id == project_id)
        if status:
            query = query.where(Scan.status == status)
        if search:
            query = query.where(
                or_(
                    Scan.scan_uid.ilike(f"%{search}%"),
                    Scan.main_street.ilike(f"%{search}%"),
                    Scan.city.ilike(f"%{search}%"),
                    Scan.project_name.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(Scan.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: ScanCreate) -> Scan:
        db_obj = Scan(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Scan, obj_in: ScanUpdate) -> Scan:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[Scan]:
        obj = db.get(Scan, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

scan = CRUDScan()

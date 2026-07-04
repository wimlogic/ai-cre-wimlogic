from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.scan_job import ScanJob
from app.schemas.scan_job import ScanJobCreate, ScanJobUpdate

class CRUDScanJob:
    def get(self, db: Session, id: int) -> Optional[ScanJob]:
        return db.get(ScanJob, id)

    def get_by_scan_id(self, db: Session, scan_id: str) -> Optional[ScanJob]:
        statement = select(ScanJob).where(ScanJob.scan_id == scan_id)
        return db.execute(statement).scalars().first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, project_id: Optional[str] = None, status: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[ScanJob], int]:
        query = select(ScanJob)
        
        # Apply filters
        if project_id:
            query = query.where(ScanJob.project_id == project_id)
        if status:
            query = query.where(ScanJob.status == status)
        if search:
            query = query.where(
                or_(
                    ScanJob.project_name.ilike(f"%{search}%"),
                    ScanJob.main_street.ilike(f"%{search}%"),
                    ScanJob.notes.ilike(f"%{search}%"),
                    ScanJob.scan_id.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(ScanJob.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: ScanJobCreate) -> ScanJob:
        db_obj = ScanJob(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: ScanJob, obj_in: ScanJobUpdate) -> ScanJob:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[ScanJob]:
        obj = db.get(ScanJob, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

scan_job = CRUDScanJob()

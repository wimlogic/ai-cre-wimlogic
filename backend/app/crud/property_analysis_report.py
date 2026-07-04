from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.property_analysis_report import PropertyAnalysisReport
from app.schemas.property_analysis_report import PropertyAnalysisReportCreate, PropertyAnalysisReportUpdate

class CRUDPropertyAnalysisReport:
    def get(self, db: Session, id: int) -> Optional[PropertyAnalysisReport]:
        return db.get(PropertyAnalysisReport, id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, project_id: Optional[str] = None, property_id: Optional[int] = None, search: Optional[str] = None
    ) -> Tuple[List[PropertyAnalysisReport], int]:
        query = select(PropertyAnalysisReport)
        
        # Apply filters
        if project_id:
            query = query.where(PropertyAnalysisReport.project_id == project_id)
        if property_id:
            query = query.where(PropertyAnalysisReport.property_id == property_id)
        if search:
            query = query.where(
                or_(
                    PropertyAnalysisReport.zoning_notes.ilike(f"%{search}%"),
                    PropertyAnalysisReport.risk_notes.ilike(f"%{search}%"),
                    PropertyAnalysisReport.recommendation.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(PropertyAnalysisReport.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: PropertyAnalysisReportCreate) -> PropertyAnalysisReport:
        db_obj = PropertyAnalysisReport(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: PropertyAnalysisReport, obj_in: PropertyAnalysisReportUpdate) -> PropertyAnalysisReport:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[PropertyAnalysisReport]:
        obj = db.get(PropertyAnalysisReport, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

property_analysis_report = CRUDPropertyAnalysisReport()

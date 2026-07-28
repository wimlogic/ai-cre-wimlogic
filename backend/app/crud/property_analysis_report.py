from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, desc
from app.models.property_analysis_report import PropertyAnalysisReport
from app.schemas.property_analysis_report import PropertyAnalysisReportCreate, PropertyAnalysisReportUpdate

class CRUDPropertyAnalysisReport:
    def get(self, db: Session, id: int) -> Optional[PropertyAnalysisReport]:
        return db.get(PropertyAnalysisReport, id)

    def get_latest_completed_for_project_property(
        self, db: Session, *, project_id: str, property_id: int
    ) -> Optional[PropertyAnalysisReport]:
        """
        AI HOME Knowledge Inheritance V1.0 - inheritance_04_backend_implementation.md
        §8.4. Deterministic Property Analysis Report resolver.

        Resolution is by the EXPLICIT (project_id, property_id) pair - never by
        property_id alone - matching the same "no first-association inference"
        rule already enforced elsewhere for Design Job Project/Property
        validation (crud_project_property.get_multi(), design_job_service.py).

        Eligibility: matches both identifiers, workflow_status == "Completed"
        (the exact, already-used success value - confirmed via source
        inspection of result_sync.py, which sets this literal string when a
        Property Analysis Report is created from a completed workflow result;
        not invented for this feature), and completed_at is not null.

        Deterministic ordering: completed_at DESC, then id DESC as a tiebreaker
        for equal timestamps. Never uses `.first()` without explicit ordering,
        never `associations[0]`.

        Pure query logic only, per spec: returns one model instance or None.
        Does not normalize output (see payload_builder._build_property_ai_analysis
        for that), does not raise business-layer validation exceptions, does
        not commit or rollback.
        """
        statement = (
            select(PropertyAnalysisReport)
            .where(PropertyAnalysisReport.project_id == project_id)
            .where(PropertyAnalysisReport.property_id == property_id)
            .where(PropertyAnalysisReport.workflow_status == "Completed")
            .where(PropertyAnalysisReport.completed_at.is_not(None))
            .order_by(desc(PropertyAnalysisReport.completed_at), desc(PropertyAnalysisReport.id))
            .limit(1)
        )
        return db.execute(statement).scalars().first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, project_id: Optional[str] = None,
        property_id: Optional[int] = None, workflow_result_id: Optional[int] = None, search: Optional[str] = None
    ) -> Tuple[List[PropertyAnalysisReport], int]:
        query = select(PropertyAnalysisReport)
        
        # Apply filters
        if project_id:
            query = query.where(PropertyAnalysisReport.project_id == project_id)
        if property_id:
            query = query.where(PropertyAnalysisReport.property_id == property_id)
        if workflow_result_id:
            query = query.where(PropertyAnalysisReport.workflow_result_id == workflow_result_id)
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

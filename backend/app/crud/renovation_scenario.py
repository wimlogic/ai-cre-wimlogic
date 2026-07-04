from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.renovation_scenario import RenovationScenario
from app.schemas.renovation_scenario import RenovationScenarioCreate, RenovationScenarioUpdate

class CRUDRenovationScenario:
    def get(self, db: Session, id: int) -> Optional[RenovationScenario]:
        return db.get(RenovationScenario, id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, project_id: Optional[str] = None, property_id: Optional[int] = None, status: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[RenovationScenario], int]:
        query = select(RenovationScenario)
        
        # Apply filters
        if project_id:
            query = query.where(RenovationScenario.project_id == project_id)
        if property_id:
            query = query.where(RenovationScenario.property_id == property_id)
        if status:
            query = query.where(RenovationScenario.status == status)
        if search:
            query = query.where(
                or_(
                    RenovationScenario.scenario_name.ilike(f"%{search}%"),
                    RenovationScenario.rationale.ilike(f"%{search}%"),
                    RenovationScenario.custom_notes.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(RenovationScenario.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: RenovationScenarioCreate) -> RenovationScenario:
        db_obj = RenovationScenario(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: RenovationScenario, obj_in: RenovationScenarioUpdate) -> RenovationScenario:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[RenovationScenario]:
        obj = db.get(RenovationScenario, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

renovation_scenario = CRUDRenovationScenario()

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.design_tool_image_requirement import DesignToolImageRequirement
from app.schemas.design_tool_image_requirement import DesignToolImageRequirementCreate, DesignToolImageRequirementUpdate

class CRUDDesignToolImageRequirement:
    def get(self, db: Session, id: int) -> Optional[DesignToolImageRequirement]:
        return db.get(DesignToolImageRequirement, id)

    def get_by_tool_and_role(self, db: Session, *, tool_id: int, input_role: str) -> Optional[DesignToolImageRequirement]:
        statement = select(DesignToolImageRequirement).where(
            DesignToolImageRequirement.tool_id == tool_id,
            DesignToolImageRequirement.input_role == input_role,
        )
        return db.execute(statement).scalars().first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, tool_id: Optional[int] = None
    ) -> Tuple[List[DesignToolImageRequirement], int]:
        query = select(DesignToolImageRequirement)

        if tool_id is not None:
            query = query.where(DesignToolImageRequirement.tool_id == tool_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()

        statement = query.order_by(DesignToolImageRequirement.display_order.asc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()

        return list(results), total_count

    def create(self, db: Session, *, obj_in: DesignToolImageRequirementCreate, commit: bool = True) -> DesignToolImageRequirement:
        db_obj = DesignToolImageRequirement(**obj_in.model_dump())
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def update(self, db: Session, *, db_obj: DesignToolImageRequirement, obj_in: DesignToolImageRequirementUpdate, commit: bool = True) -> DesignToolImageRequirement:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def remove(self, db: Session, *, id: int, commit: bool = True) -> Optional[DesignToolImageRequirement]:
        obj = db.get(DesignToolImageRequirement, id)
        if obj:
            db.delete(obj)
            if commit:
                db.commit()
            else:
                db.flush()
        return obj

design_tool_image_requirement = CRUDDesignToolImageRequirement()

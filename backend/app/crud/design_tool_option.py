from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.design_tool_option import DesignToolOption
from app.schemas.design_tool_option import DesignToolOptionCreate, DesignToolOptionUpdate

class CRUDDesignToolOption:
    def get(self, db: Session, id: int) -> Optional[DesignToolOption]:
        return db.get(DesignToolOption, id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, tool_id: Optional[int] = None
    ) -> Tuple[List[DesignToolOption], int]:
        query = select(DesignToolOption)

        if tool_id is not None:
            query = query.where(DesignToolOption.tool_id == tool_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()

        statement = query.order_by(DesignToolOption.display_order.asc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()

        return list(results), total_count

    def create(self, db: Session, *, obj_in: DesignToolOptionCreate, commit: bool = True) -> DesignToolOption:
        db_obj = DesignToolOption(**obj_in.model_dump())
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def update(self, db: Session, *, db_obj: DesignToolOption, obj_in: DesignToolOptionUpdate, commit: bool = True) -> DesignToolOption:
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

    def remove(self, db: Session, *, id: int, commit: bool = True) -> Optional[DesignToolOption]:
        obj = db.get(DesignToolOption, id)
        if obj:
            db.delete(obj)
            if commit:
                db.commit()
            else:
                db.flush()
        return obj

design_tool_option = CRUDDesignToolOption()

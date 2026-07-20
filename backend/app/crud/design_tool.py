from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.design_tool import DesignTool
from app.schemas.design_tool import DesignToolCreate, DesignToolUpdate

class CRUDDesignTool:
    def get(self, db: Session, id: int) -> Optional[DesignTool]:
        return db.get(DesignTool, id)

    def get_by_tool_code(self, db: Session, tool_code: str) -> Optional[DesignTool]:
        statement = select(DesignTool).where(DesignTool.tool_code == tool_code)
        return db.execute(statement).scalars().first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, status: Optional[str] = None, design_type: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[DesignTool], int]:
        query = select(DesignTool)

        if status:
            query = query.where(DesignTool.status == status)
        if design_type:
            query = query.where(DesignTool.design_type == design_type)
        if search:
            query = query.where(
                or_(
                    DesignTool.tool_code.ilike(f"%{search}%"),
                    DesignTool.tool_name.ilike(f"%{search}%")
                )
            )

        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()

        statement = query.order_by(DesignTool.display_order.asc(), DesignTool.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()

        return list(results), total_count

    def create(self, db: Session, *, obj_in: DesignToolCreate, commit: bool = True) -> DesignTool:
        """
        commit=True (default): standalone use - commits and refreshes.
        commit=False: participates in a service-owned transaction - only
        flushes (so db_obj.id is populated for the caller) and does NOT
        commit or roll back. The calling service owns commit/rollback.
        """
        db_obj = DesignTool(**obj_in.model_dump())
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def update(self, db: Session, *, db_obj: DesignTool, obj_in: DesignToolUpdate, commit: bool = True) -> DesignTool:
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

    def remove(self, db: Session, *, id: int, commit: bool = True) -> Optional[DesignTool]:
        obj = db.get(DesignTool, id)
        if obj:
            db.delete(obj)
            if commit:
                db.commit()
            else:
                db.flush()
        return obj

design_tool = CRUDDesignTool()

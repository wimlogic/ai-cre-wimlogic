from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete
from app.models.design_job_image import DesignJobImage
from app.schemas.design_job_image import DesignJobImageCreate

class CRUDDesignJobImage:
    def get(self, db: Session, id: int) -> Optional[DesignJobImage]:
        return db.get(DesignJobImage, id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, design_job_id: Optional[int] = None
    ) -> Tuple[List[DesignJobImage], int]:
        query = select(DesignJobImage)

        if design_job_id is not None:
            query = query.where(DesignJobImage.design_job_id == design_job_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()

        statement = query.order_by(DesignJobImage.display_order.asc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()

        return list(results), total_count

    def create(self, db: Session, *, obj_in: DesignJobImageCreate, commit: bool = True) -> DesignJobImage:
        """
        commit=False participates in the Configure Design Job Images
        transaction (delete existing selection + insert replacement rows
        as one atomic unit) - pair with remove_by_design_job(..., commit=False).
        """
        db_obj = DesignJobImage(**obj_in.model_dump())
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def remove_by_design_job(self, db: Session, *, design_job_id: int, commit: bool = True) -> int:
        """
        Deletes every selected-image row for a Design Job in one statement.
        Used by the Configure Images service action, which replaces the
        entire selected-image set (delete-then-recreate) rather than doing
        a per-row diff - a pure DB operation, the "replace" decision itself
        is a service-layer concern. Returns the number of rows deleted.

        commit=False: does not commit or roll back - flushes so the delete
        is visible to subsequent statements within the same service-owned
        transaction (e.g. the replacement inserts that follow). A failure
        during those inserts and a subsequent service-issued rollback will
        restore the original rows, since nothing here was ever committed.
        """
        statement = delete(DesignJobImage).where(DesignJobImage.design_job_id == design_job_id)
        result = db.execute(statement)
        if commit:
            db.commit()
        else:
            db.flush()
        return result.rowcount

    def remove(self, db: Session, *, id: int, commit: bool = True) -> Optional[DesignJobImage]:
        obj = db.get(DesignJobImage, id)
        if obj:
            db.delete(obj)
            if commit:
                db.commit()
            else:
                db.flush()
        return obj

design_job_image = CRUDDesignJobImage()

from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.design_image_lineage import DesignImageLineage

class CRUDDesignImageLineage:
    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, image_version_id: Optional[int] = None
    ) -> Tuple[List[DesignImageLineage], int]:
        query = select(DesignImageLineage)

        if image_version_id is not None:
            query = query.where(DesignImageLineage.image_version_id == image_version_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()

        statement = query.order_by(DesignImageLineage.created_at.asc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()

        return list(results), total_count

    def create(self, db: Session, *, obj_in: Dict[str, Any], commit: bool = True) -> DesignImageLineage:
        """
        No public Create schema exists (Checkpoint 2: read-only through the
        public API, written only by workflow result ingestion alongside
        Design Image Version persistence). Expected keys: image_version_id,
        source_type, source_property_image_id OR source_image_version_id
        (mutually exclusive per the source_xor CHECK constraint),
        lineage_role. No update() method - lineage rows are immutable once
        written, per the locked Image Lineage architecture.

        commit=False participates in the Image Version + Lineage Ingestion
        transaction - pair with design_image_version.create(..., commit=False)
        so the version row and every one of its lineage rows commit or
        roll back together as a single unit.
        """
        db_obj = DesignImageLineage(**obj_in)
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

design_image_lineage = CRUDDesignImageLineage()

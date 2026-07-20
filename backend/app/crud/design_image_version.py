from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.design_image_version import DesignImageVersion

class CRUDDesignImageVersion:
    def get(self, db: Session, id: int) -> Optional[DesignImageVersion]:
        return db.get(DesignImageVersion, id)

    def get_by_uid(self, db: Session, version_uid: str) -> Optional[DesignImageVersion]:
        statement = select(DesignImageVersion).where(DesignImageVersion.version_uid == version_uid)
        return db.execute(statement).scalars().first()

    def get_max_version_number(self, db: Session, *, design_job_id: int) -> int:
        statement = select(func.max(DesignImageVersion.version_number)).where(DesignImageVersion.design_job_id == design_job_id)
        result = db.execute(statement).scalar_one_or_none()
        return result or 0

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, design_job_id: Optional[int] = None, property_id: Optional[int] = None, status: Optional[str] = None
    ) -> Tuple[List[DesignImageVersion], int]:
        query = select(DesignImageVersion)

        if design_job_id is not None:
            query = query.where(DesignImageVersion.design_job_id == design_job_id)
        if property_id is not None:
            query = query.where(DesignImageVersion.property_id == property_id)
        if status:
            query = query.where(DesignImageVersion.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()

        statement = query.order_by(DesignImageVersion.design_job_id.asc(), DesignImageVersion.version_number.asc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()

        return list(results), total_count

    def create(self, db: Session, *, obj_in: Dict[str, Any], commit: bool = True) -> DesignImageVersion:
        """
        No public Create schema exists (Checkpoint 2: Design Image Versions
        are created by workflow result ingestion, not a public POST).
        Expected keys match the cre_design_image_versions columns, e.g.
        version_uid, design_job_id, property_id, workflow_execution_id,
        version_number, file_name, storage_path, thumbnail_path, mime_type,
        file_size, width, height, status, generated_at, generated_by.

        commit=False participates in the Image Version + Lineage Ingestion
        transaction (create the version row + create all its lineage rows
        as one atomic unit) - a version must never persist with partial or
        missing lineage. Pair with design_image_lineage.create(..., commit=False)
        for each source, and let the calling service commit once at the end.
        """
        db_obj = DesignImageVersion(**obj_in)
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def update(self, db: Session, *, db_obj: DesignImageVersion, obj_in: Dict[str, Any], commit: bool = True) -> DesignImageVersion:
        """
        Used for status transitions (generated -> approved / rejected /
        superseded) and optional generated_asset_id promotion. No public
        Update schema exists, for the same reason as create() above.
        """
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

design_image_version = CRUDDesignImageVersion()

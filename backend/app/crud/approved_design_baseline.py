from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.approved_design_baseline import ApprovedDesignBaseline

class CRUDApprovedDesignBaseline:
    def get(self, db: Session, id: int) -> Optional[ApprovedDesignBaseline]:
        return db.get(ApprovedDesignBaseline, id)

    def get_by_uid(self, db: Session, baseline_uid: str) -> Optional[ApprovedDesignBaseline]:
        statement = select(ApprovedDesignBaseline).where(ApprovedDesignBaseline.baseline_uid == baseline_uid)
        return db.execute(statement).scalars().first()

    def get_active(self, db: Session, *, property_id: int, design_type: str, design_scope: str) -> Optional[ApprovedDesignBaseline]:
        """
        Looks up the current active baseline for a scope via
        active_scope_key, using the exact same "property_id|design_type|
        design_scope" format the database's GENERATED ALWAYS expression
        computes (this column is NULL for any non-active row, so a match
        here can only ever be the one active row for that scope, if one
        exists - the uniqueness itself is enforced by the DB constraint,
        not by this query).
        """
        scope_key = f"{property_id}|{design_type}|{design_scope}"
        statement = select(ApprovedDesignBaseline).where(ApprovedDesignBaseline.active_scope_key == scope_key)
        return db.execute(statement).scalars().first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, property_id: Optional[int] = None, status: Optional[str] = None, design_type: Optional[str] = None, design_scope: Optional[str] = None
    ) -> Tuple[List[ApprovedDesignBaseline], int]:
        query = select(ApprovedDesignBaseline)

        if property_id is not None:
            query = query.where(ApprovedDesignBaseline.property_id == property_id)
        if status:
            query = query.where(ApprovedDesignBaseline.status == status)
        if design_type:
            query = query.where(ApprovedDesignBaseline.design_type == design_type)
        if design_scope:
            query = query.where(ApprovedDesignBaseline.design_scope == design_scope)

        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()

        statement = query.order_by(ApprovedDesignBaseline.approved_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()

        return list(results), total_count

    def create(self, db: Session, *, obj_in: Dict[str, Any], commit: bool = True) -> ApprovedDesignBaseline:
        """
        No public Create schema exists (Checkpoint 2: baselines are only
        created via the approve action). active_scope_key must NEVER be a
        key in obj_in - it is database-computed (Computed/STORED) and will
        be rejected by MySQL if supplied explicitly. Expected keys match
        the cre_approved_design_baselines columns: baseline_uid,
        project_id, property_id, design_job_id, image_version_id, tool_id,
        tool_code, design_type, design_scope, tool_options_json,
        effective_context_json, submitted_payload_json, approved_by,
        approved_at. status defaults to 'active' via the ORM column default.

        commit=False participates in the Approved Design Baseline
        supersede transaction (flip prior active baseline to superseded +
        insert the new active baseline as one atomic unit) - pair with
        update(..., commit=False) on the prior baseline.
        """
        if "active_scope_key" in obj_in:
            raise ValueError("active_scope_key is database-generated and cannot be assigned")
        db_obj = ApprovedDesignBaseline(**obj_in)
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def update(self, db: Session, *, db_obj: ApprovedDesignBaseline, obj_in: Dict[str, Any], commit: bool = True) -> ApprovedDesignBaseline:
        """
        Used to flip status to 'superseded' during the baseline supersede
        transaction. active_scope_key must NEVER be a key in obj_in, for
        the same reason as create() above - the database recomputes it
        automatically the moment status changes.
        """
        if "active_scope_key" in obj_in:
            raise ValueError("active_scope_key is database-generated and cannot be assigned")
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

approved_design_baseline = CRUDApprovedDesignBaseline()

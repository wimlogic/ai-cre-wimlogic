from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.generated_asset import GeneratedAsset
from app.schemas.generated_asset import GeneratedAssetCreate, GeneratedAssetUpdate

class CRUDGeneratedAsset:
    def get(self, db: Session, asset_id: int) -> Optional[GeneratedAsset]:
        return db.get(GeneratedAsset, asset_id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, property_id: Optional[int] = None, execution_id: Optional[int] = None, asset_type: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[GeneratedAsset], int]:
        query = select(GeneratedAsset)
        
        # Apply filters
        if property_id:
            query = query.where(GeneratedAsset.property_id == property_id)
        if execution_id:
            query = query.where(GeneratedAsset.execution_id == execution_id)
        if asset_type:
            query = query.where(GeneratedAsset.asset_type == asset_type)
        if search:
            query = query.where(
                or_(
                    GeneratedAsset.title.ilike(f"%{search}%"),
                    GeneratedAsset.description.ilike(f"%{search}%"),
                    GeneratedAsset.file_name.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(GeneratedAsset.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: GeneratedAssetCreate) -> GeneratedAsset:
        db_obj = GeneratedAsset(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: GeneratedAsset, obj_in: GeneratedAssetUpdate) -> GeneratedAsset:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, asset_id: int) -> Optional[GeneratedAsset]:
        obj = db.get(GeneratedAsset, asset_id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

generated_asset = CRUDGeneratedAsset()

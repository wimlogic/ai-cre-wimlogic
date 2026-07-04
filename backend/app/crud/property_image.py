from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.property_image import PropertyImage
from app.schemas.property_image import PropertyImageCreate, PropertyImageUpdate

class CRUDPropertyImage:
    def get(self, db: Session, id: int) -> Optional[PropertyImage]:
        return db.get(PropertyImage, id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, property_id: Optional[int] = None, project_id: Optional[str] = None, image_type: Optional[str] = None, include_deleted: bool = False, search: Optional[str] = None
    ) -> Tuple[List[PropertyImage], int]:
        query = select(PropertyImage)
        
        # Apply filters
        if not include_deleted:
            query = query.where(PropertyImage.is_deleted == 0)
        if property_id:
            query = query.where(PropertyImage.property_id == property_id)
        if project_id:
            query = query.where(PropertyImage.project_id == project_id)
        if image_type:
            query = query.where(PropertyImage.image_type == image_type)
        if search:
            query = query.where(
                or_(
                    PropertyImage.provider.ilike(f"%{search}%"),
                    PropertyImage.notes.ilike(f"%{search}%"),
                    PropertyImage.original_file_name.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.order_by(PropertyImage.created_at.desc()).offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: PropertyImageCreate) -> PropertyImage:
        db_obj = PropertyImage(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: PropertyImage, obj_in: PropertyImageUpdate) -> PropertyImage:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[PropertyImage]:
        obj = db.get(PropertyImage, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

property_image = CRUDPropertyImage()

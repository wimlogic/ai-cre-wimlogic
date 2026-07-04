from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyUpdate

class CRUDProperty:
    def get(self, db: Session, id: int) -> Optional[Property]:
        return db.get(Property, id)

    def get_by_uid(self, db: Session, property_uid: str) -> Optional[Property]:
        statement = select(Property).where(Property.property_uid == property_uid)
        return db.execute(statement).scalars().first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, city: Optional[str] = None, state: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[Property], int]:
        query = select(Property)
        
        # Apply filters
        if city:
            query = query.where(Property.city == city)
        if state:
            query = query.where(Property.state == state)
        if search:
            query = query.where(
                or_(
                    Property.address.ilike(f"%{search}%"),
                    Property.city.ilike(f"%{search}%"),
                    Property.zip.ilike(f"%{search}%"),
                    Property.apn.ilike(f"%{search}%"),
                    Property.property_uid.ilike(f"%{search}%")
                )
            )
            
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar_one()
        
        # Paginate
        statement = query.offset(skip).limit(limit)
        results = db.execute(statement).scalars().all()
        
        return list(results), total_count

    def create(self, db: Session, *, obj_in: PropertyCreate) -> Property:
        db_obj = Property(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Property, obj_in: PropertyUpdate) -> Property:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[Property]:
        obj = db.get(Property, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

property = CRUDProperty()

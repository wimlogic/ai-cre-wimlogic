from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.crud.property import property as crud_property
from app.schemas.property import PropertyCreate, PropertyUpdate
from app.models.property import Property

class PropertyService:
    def get_property(self, db: Session, id: int) -> Optional[Property]:
        """Retrieve a property by its database primary key ID."""
        return crud_property.get(db, id)

    def get_property_by_uid(self, db: Session, property_uid: str) -> Optional[Property]:
        """Retrieve a property by its unique external property_uid identifier."""
        return crud_property.get_by_uid(db, property_uid)

    def get_properties(
        self, db: Session, skip: int = 0, limit: int = 100, city: Optional[str] = None, state: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[Property], int]:
        """Get a list of properties with pagination, city/state filtering, and search options."""
        return crud_property.get_multi(db, skip=skip, limit=limit, city=city, state=state, search=search)

    def create_property(self, db: Session, property_in: PropertyCreate) -> Property:
        """Create a new property after verifying property_uid uniqueness."""
        if property_in.property_uid:
            existing = crud_property.get_by_uid(db, property_in.property_uid)
            if existing:
                raise ValueError(f"Property with property_uid '{property_in.property_uid}' already exists")
        return crud_property.create(db, obj_in=property_in)

    def update_property(self, db: Session, id: int, property_in: PropertyUpdate) -> Optional[Property]:
        """Update an existing property by primary key ID, ensuring unique constraints are preserved."""
        db_obj = crud_property.get(db, id)
        if not db_obj:
            return None
        if property_in.property_uid and property_in.property_uid != db_obj.property_uid:
            existing = crud_property.get_by_uid(db, property_in.property_uid)
            if existing:
                raise ValueError(f"Property with property_uid '{property_in.property_uid}' already exists")
        return crud_property.update(db, db_obj=db_obj, obj_in=property_in)

    def delete_property(self, db: Session, id: int) -> Optional[Property]:
        """Delete a property by primary key ID."""
        return crud_property.remove(db, id=id)

property_service = PropertyService()

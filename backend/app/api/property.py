from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.crud.property import property as crud_property
from app.schemas import PropertyCreate, PropertyUpdate, PropertyResponse, PropertyListResponse
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=PropertyResponse, status_code=201)
def create_property(obj_in: PropertyCreate, db: Session = Depends(get_db)):
    if obj_in.property_uid:
        existing = crud_property.get_by_uid(db, obj_in.property_uid)
        if existing:
            raise HTTPException(status_code=400, detail=f"Property with property_uid '{obj_in.property_uid}' already exists")
    return crud_property.create(db, obj_in=obj_in)

@router.get("/{id}", response_model=PropertyResponse)
def get_property(id: int, db: Session = Depends(get_db)):
    db_obj = crud_property.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    return db_obj

@router.get("/by-uid/{property_uid}", response_model=PropertyResponse)
def get_property_by_uid(property_uid: str, db: Session = Depends(get_db)):
    db_obj = crud_property.get_by_uid(db, property_uid)
    if not db_obj:
        raise HTTPException(status_code=404, detail=f"Property with UID '{property_uid}' not found")
    return db_obj

@router.get("/", response_model=PropertyListResponse)
def list_properties(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = crud_property.get_multi(
        db, skip=skip, limit=limit, city=city, state=state, search=search
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=PropertyResponse)
def update_property(id: int, obj_in: PropertyUpdate, db: Session = Depends(get_db)):
    db_obj = crud_property.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    if obj_in.property_uid and obj_in.property_uid != db_obj.property_uid:
        existing = crud_property.get_by_uid(db, obj_in.property_uid)
        if existing:
            raise HTTPException(status_code=400, detail=f"Property with property_uid '{obj_in.property_uid}' already exists")
    return crud_property.update(db, db_obj=db_obj, obj_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_property(id: int, db: Session = Depends(get_db)):
    db_obj = crud_property.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    crud_property.remove(db, id=id)
    return {"success": True}

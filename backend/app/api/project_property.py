from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.crud.project_property import project_property as crud_project_property
from app.schemas import ProjectPropertyCreate, ProjectPropertyUpdate, ProjectPropertyResponse, ProjectPropertyListResponse
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=ProjectPropertyResponse, status_code=201)
def create_project_property(obj_in: ProjectPropertyCreate, db: Session = Depends(get_db)):
    return crud_project_property.create(db, obj_in=obj_in)

@router.get("/{id}", response_model=ProjectPropertyResponse)
def get_project_property(id: int, db: Session = Depends(get_db)):
    db_obj = crud_project_property.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Project-property association not found")
    return db_obj

@router.get("/", response_model=ProjectPropertyListResponse)
def list_project_properties(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    project_id: Optional[str] = Query(None),
    property_id: Optional[int] = Query(None),
    scan_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = crud_project_property.get_multi(
        db, skip=skip, limit=limit, project_id=project_id, property_id=property_id, scan_id=scan_id
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=ProjectPropertyResponse)
def update_project_property(id: int, obj_in: ProjectPropertyUpdate, db: Session = Depends(get_db)):
    db_obj = crud_project_property.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Project-property association not found")
    return crud_project_property.update(db, db_obj=db_obj, obj_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_project_property(id: int, db: Session = Depends(get_db)):
    db_obj = crud_project_property.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Project-property association not found")
    crud_project_property.remove(db, id=id)
    return {"success": True}

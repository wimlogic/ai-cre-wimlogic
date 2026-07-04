from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.crud.zoning_note import zoning_note as crud_zoning_note
from app.schemas import ZoningNoteCreate, ZoningNoteUpdate, ZoningNoteResponse, ZoningNoteListResponse
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=ZoningNoteResponse, status_code=201)
def create_zoning_note(obj_in: ZoningNoteCreate, db: Session = Depends(get_db)):
    return crud_zoning_note.create(db, obj_in=obj_in)

@router.get("/{id}", response_model=ZoningNoteResponse)
def get_zoning_note(id: int, db: Session = Depends(get_db)):
    db_obj = crud_zoning_note.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Zoning note not found")
    return db_obj

@router.get("/", response_model=ZoningNoteListResponse)
def list_zoning_notes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    property_id: Optional[int] = Query(None),
    entitlement_risk: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = crud_zoning_note.get_multi(
        db, skip=skip, limit=limit, property_id=property_id, entitlement_risk=entitlement_risk, search=search
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=ZoningNoteResponse)
def update_zoning_note(id: int, obj_in: ZoningNoteUpdate, db: Session = Depends(get_db)):
    db_obj = crud_zoning_note.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Zoning note not found")
    return crud_zoning_note.update(db, db_obj=db_obj, obj_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_zoning_note(id: int, db: Session = Depends(get_db)):
    db_obj = crud_zoning_note.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Zoning note not found")
    crud_zoning_note.remove(db, id=id)
    return {"success": True}

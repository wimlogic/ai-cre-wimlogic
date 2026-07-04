from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.crud.concept_design import concept_design as crud_concept_design
from app.schemas import ConceptDesignCreate, ConceptDesignUpdate, ConceptDesignResponse, ConceptDesignListResponse
from pydantic import BaseModel

router = APIRouter()

class DeleteResponse(BaseModel):
    success: bool = True

@router.post("/", response_model=ConceptDesignResponse, status_code=201)
def create_concept_design(obj_in: ConceptDesignCreate, db: Session = Depends(get_db)):
    return crud_concept_design.create(db, obj_in=obj_in)

@router.get("/{id}", response_model=ConceptDesignResponse)
def get_concept_design(id: int, db: Session = Depends(get_db)):
    db_obj = crud_concept_design.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Concept design not found")
    return db_obj

@router.get("/", response_model=ConceptDesignListResponse)
def list_concept_designs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    project_id: Optional[str] = Query(None),
    property_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    items, total = crud_concept_design.get_multi(
        db, skip=skip, limit=limit, project_id=project_id, property_id=property_id, status=status, search=search
    )
    return {"count": total, "items": items}

@router.put("/{id}", response_model=ConceptDesignResponse)
def update_concept_design(id: int, obj_in: ConceptDesignUpdate, db: Session = Depends(get_db)):
    db_obj = crud_concept_design.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Concept design not found")
    return crud_concept_design.update(db, db_obj=db_obj, obj_in=obj_in)

@router.delete("/{id}", response_model=DeleteResponse)
def delete_concept_design(id: int, db: Session = Depends(get_db)):
    db_obj = crud_concept_design.get(db, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Concept design not found")
    crud_concept_design.remove(db, id=id)
    return {"success": True}

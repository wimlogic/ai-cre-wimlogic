"""
api/design_studio_tool.py

AI HOME WIMLOGIC -- Design Studio -- V1.1C Tool Box
Enterprise API Router

Purpose
-------
HTTP router for the Design Studio Tool Box business resource:
    - Tool catalog (Design Studio business actions, e.g. Exterior Remodel)
    - Tool Options (per-Tool configurable settings)
    - Tool Image Requirements (per-Tool image-count/role validation rules -
      the sole source of truth for image-count validation; see
      DesignTool schema, which deliberately carries no
      min_image_count/max_image_count of its own)
    - Tool Knowledge Rules (per-Tool Knowledge usage rules - simplified
      structure only, no usage_mode/rule_json)

Mounted at /api/v1/design-studio/tools per the approved Decision 3
namespace.

Architecture Compliance
-------------------------
Routers contain HTTP only. This file performs NO business logic and no
direct CRUD/model access - everything is delegated to the Design Studio
Tool Box service layer (app.services.design_tool_service and its three
sibling services for options/image-requirements/knowledge-rules).

Nested Resource Ownership
--------------------------
Every nested GET/PUT/DELETE action (options, image-requirements,
knowledge-rules) is ownership-scoped by the path tool_id: the service
verifies child.tool_id == path tool_id before returning, updating, or
deleting the child. A child that exists but belongs to a different Tool
surfaces as 404, not as evidence that the child exists elsewhere - the
router never distinguishes "not found" from "belongs to another Tool"
in its response.

A Tool is a Design Studio business action. A Tool is NOT a DEV-TOOLS
Workflow and NOT a Design Type - multiple Tools may share a Design Type
or workflow family.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import (
    DesignToolCreate,
    DesignToolUpdate,
    DesignToolResponse,
    DesignToolListResponse,
    DesignToolOptionCreate,
    DesignToolOptionUpdate,
    DesignToolOptionRead,
    DesignToolImageRequirementCreate,
    DesignToolImageRequirementUpdate,
    DesignToolImageRequirementRead,
    DesignToolKnowledgeRuleCreate,
    DesignToolKnowledgeRuleUpdate,
    DesignToolKnowledgeRuleRead,
)
from app.services.design_tool_service import design_tool_service, DesignToolReferencedError
from app.services.design_tool_option_service import design_tool_option_service
from app.services.design_tool_image_requirement_service import design_tool_image_requirement_service
from app.services.design_tool_knowledge_rule_service import design_tool_knowledge_rule_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Tool catalog
# ---------------------------------------------------------------------------

@router.post("/", response_model=DesignToolResponse, status_code=201)
def create_tool(obj_in: DesignToolCreate, db: Session = Depends(get_db)):
    try:
        return design_tool_service.create_tool(db, tool_in=obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{tool_id}", response_model=DesignToolResponse)
def get_tool(tool_id: int, db: Session = Depends(get_db)):
    db_obj = design_tool_service.get_tool(db, tool_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Design Tool not found")
    return db_obj


@router.get("/", response_model=DesignToolListResponse)
def list_tools(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None),
    design_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    items, total = design_tool_service.get_tools(db, skip=skip, limit=limit, status=status, design_type=design_type, search=search)
    return {"count": total, "items": items}


@router.put("/{tool_id}", response_model=DesignToolResponse)
def update_tool(tool_id: int, obj_in: DesignToolUpdate, db: Session = Depends(get_db)):
    try:
        db_obj = design_tool_service.update_tool(db, tool_id, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not db_obj:
        raise HTTPException(status_code=404, detail="Design Tool not found")
    return db_obj


@router.delete("/{tool_id}", status_code=204)
def delete_tool(tool_id: int, db: Session = Depends(get_db)):
    try:
        db_obj = design_tool_service.delete_tool(db, tool_id)
    except DesignToolReferencedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not db_obj:
        raise HTTPException(status_code=404, detail="Design Tool not found")
    return None


# ---------------------------------------------------------------------------
# Tool Options
# ---------------------------------------------------------------------------

@router.post("/{tool_id}/options", response_model=DesignToolOptionRead, status_code=201)
def create_tool_option(tool_id: int, obj_in: DesignToolOptionCreate, db: Session = Depends(get_db)):
    # The URL path is authoritative for tool_id; any tool_id in the body is overridden.
    obj_in = obj_in.model_copy(update={"tool_id": tool_id})
    try:
        return design_tool_option_service.create_option(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{tool_id}/options", response_model=List[DesignToolOptionRead])
def list_tool_options(tool_id: int, db: Session = Depends(get_db)):
    items, _ = design_tool_option_service.get_options(db, tool_id=tool_id, limit=500)
    return items


@router.put("/{tool_id}/options/{option_id}", response_model=DesignToolOptionRead)
def update_tool_option(tool_id: int, option_id: int, obj_in: DesignToolOptionUpdate, db: Session = Depends(get_db)):
    try:
        db_obj = design_tool_option_service.update_option(db, tool_id=tool_id, id=option_id, option_in=obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not db_obj:
        raise HTTPException(status_code=404, detail="Tool Option not found")
    return db_obj


@router.delete("/{tool_id}/options/{option_id}", status_code=204)
def delete_tool_option(tool_id: int, option_id: int, db: Session = Depends(get_db)):
    db_obj = design_tool_option_service.delete_option(db, tool_id=tool_id, id=option_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Tool Option not found")
    return None


# ---------------------------------------------------------------------------
# Tool Image Requirements
# ---------------------------------------------------------------------------

@router.post("/{tool_id}/image-requirements", response_model=DesignToolImageRequirementRead, status_code=201)
def create_tool_image_requirement(tool_id: int, obj_in: DesignToolImageRequirementCreate, db: Session = Depends(get_db)):
    obj_in = obj_in.model_copy(update={"tool_id": tool_id})
    try:
        return design_tool_image_requirement_service.create_requirement(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{tool_id}/image-requirements", response_model=List[DesignToolImageRequirementRead])
def list_tool_image_requirements(tool_id: int, db: Session = Depends(get_db)):
    items, _ = design_tool_image_requirement_service.get_requirements(db, tool_id=tool_id, limit=500)
    return items


@router.put("/{tool_id}/image-requirements/{requirement_id}", response_model=DesignToolImageRequirementRead)
def update_tool_image_requirement(tool_id: int, requirement_id: int, obj_in: DesignToolImageRequirementUpdate, db: Session = Depends(get_db)):
    try:
        db_obj = design_tool_image_requirement_service.update_requirement(db, tool_id=tool_id, id=requirement_id, requirement_in=obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not db_obj:
        raise HTTPException(status_code=404, detail="Tool Image Requirement not found")
    return db_obj


@router.delete("/{tool_id}/image-requirements/{requirement_id}", status_code=204)
def delete_tool_image_requirement(tool_id: int, requirement_id: int, db: Session = Depends(get_db)):
    db_obj = design_tool_image_requirement_service.delete_requirement(db, tool_id=tool_id, id=requirement_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Tool Image Requirement not found")
    return None


# ---------------------------------------------------------------------------
# Tool Knowledge Rules
# ---------------------------------------------------------------------------

@router.post("/{tool_id}/knowledge-rules", response_model=DesignToolKnowledgeRuleRead, status_code=201)
def create_tool_knowledge_rule(tool_id: int, obj_in: DesignToolKnowledgeRuleCreate, db: Session = Depends(get_db)):
    obj_in = obj_in.model_copy(update={"tool_id": tool_id})
    try:
        return design_tool_knowledge_rule_service.create_rule(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{tool_id}/knowledge-rules", response_model=List[DesignToolKnowledgeRuleRead])
def list_tool_knowledge_rules(tool_id: int, db: Session = Depends(get_db)):
    items, _ = design_tool_knowledge_rule_service.get_rules(db, tool_id=tool_id, limit=500)
    return items


@router.put("/{tool_id}/knowledge-rules/{rule_id}", response_model=DesignToolKnowledgeRuleRead)
def update_tool_knowledge_rule(tool_id: int, rule_id: int, obj_in: DesignToolKnowledgeRuleUpdate, db: Session = Depends(get_db)):
    try:
        db_obj = design_tool_knowledge_rule_service.update_rule(db, tool_id=tool_id, id=rule_id, rule_in=obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not db_obj:
        raise HTTPException(status_code=404, detail="Tool Knowledge Rule not found")
    return db_obj


@router.delete("/{tool_id}/knowledge-rules/{rule_id}", status_code=204)
def delete_tool_knowledge_rule(tool_id: int, rule_id: int, db: Session = Depends(get_db)):
    db_obj = design_tool_knowledge_rule_service.delete_rule(db, tool_id=tool_id, id=rule_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Tool Knowledge Rule not found")
    return None

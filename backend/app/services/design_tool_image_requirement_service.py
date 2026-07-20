from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.crud.design_tool import design_tool as crud_design_tool
from app.crud.design_tool_image_requirement import design_tool_image_requirement as crud_design_tool_image_requirement
from app.schemas.design_tool_image_requirement import DesignToolImageRequirementCreate, DesignToolImageRequirementUpdate
from app.models.design_tool_image_requirement import DesignToolImageRequirement

class DesignToolImageRequirementService:
    def get_requirement(self, db: Session, id: int) -> Optional[DesignToolImageRequirement]:
        return crud_design_tool_image_requirement.get(db, id)

    def get_requirement_scoped(self, db: Session, *, tool_id: int, id: int) -> Optional[DesignToolImageRequirement]:
        """
        Ownership-scoped lookup: returns the Requirement only if it both
        exists AND belongs to the given tool_id. Used by every nested
        GET/PUT/DELETE action - see DesignToolOptionService.get_option_scoped
        for the full rationale (applies identically here).
        """
        db_obj = crud_design_tool_image_requirement.get(db, id)
        if not db_obj or db_obj.tool_id != tool_id:
            return None
        return db_obj

    def get_requirements(self, db: Session, *, skip: int = 0, limit: int = 100, tool_id: Optional[int] = None) -> Tuple[List[DesignToolImageRequirement], int]:
        return crud_design_tool_image_requirement.get_multi(db, skip=skip, limit=limit, tool_id=tool_id)

    def create_requirement(self, db: Session, requirement_in: DesignToolImageRequirementCreate) -> DesignToolImageRequirement:
        """
        Business rules validated here (not in CRUD): the parent Tool must
        exist, (tool_id, input_role) must be unique, and max_count (when
        supplied) must not be less than min_count - all pre-checked for a
        clean error rather than relying on the DB constraint alone.
        """
        tool = crud_design_tool.get(db, requirement_in.tool_id)
        if not tool:
            raise ValueError(f"Tool {requirement_in.tool_id} does not exist")
        existing = crud_design_tool_image_requirement.get_by_tool_and_role(
            db, tool_id=requirement_in.tool_id, input_role=requirement_in.input_role
        )
        if existing:
            raise ValueError(f"An image requirement for role '{requirement_in.input_role}' already exists for this Tool")
        if requirement_in.max_count is not None and requirement_in.max_count < requirement_in.min_count:
            raise ValueError("max_count must not be less than min_count")
        return crud_design_tool_image_requirement.create(db, obj_in=requirement_in)

    def update_requirement(self, db: Session, *, tool_id: int, id: int, requirement_in: DesignToolImageRequirementUpdate) -> Optional[DesignToolImageRequirement]:
        """
        Ownership-checked update: the Requirement must belong to tool_id
        or this returns None (router maps to 404). If input_role is being
        changed, (tool_id, input_role) must remain unique among the
        Tool's other requirements - the current row is excluded from the
        collision check. max_count >= min_count is re-validated using the
        effective (existing + incoming) values.
        """
        db_obj = self.get_requirement_scoped(db, tool_id=tool_id, id=id)
        if not db_obj:
            return None
        if requirement_in.input_role is not None and requirement_in.input_role != db_obj.input_role:
            existing = crud_design_tool_image_requirement.get_by_tool_and_role(
                db, tool_id=tool_id, input_role=requirement_in.input_role
            )
            if existing and existing.id != id:
                raise ValueError(f"An image requirement for role '{requirement_in.input_role}' already exists for this Tool")
        effective_min = requirement_in.min_count if requirement_in.min_count is not None else db_obj.min_count
        effective_max = requirement_in.max_count if requirement_in.max_count is not None else db_obj.max_count
        if effective_max is not None and effective_max < effective_min:
            raise ValueError("max_count must not be less than min_count")
        return crud_design_tool_image_requirement.update(db, db_obj=db_obj, obj_in=requirement_in)

    def delete_requirement(self, db: Session, *, tool_id: int, id: int) -> Optional[DesignToolImageRequirement]:
        """Ownership-checked delete: the Requirement must belong to tool_id or this returns None (router maps to 404)."""
        db_obj = self.get_requirement_scoped(db, tool_id=tool_id, id=id)
        if not db_obj:
            return None
        return crud_design_tool_image_requirement.remove(db, id=id)

design_tool_image_requirement_service = DesignToolImageRequirementService()

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.crud.design_tool import design_tool as crud_design_tool
from app.crud.design_job import design_job as crud_design_job
from app.schemas.design_tool import DesignToolCreate, DesignToolUpdate
from app.models.design_tool import DesignTool

class DesignToolReferencedError(ValueError):
    """Raised when a Tool cannot be deleted because Design Jobs reference it."""
    pass

class DesignToolService:
    def get_tool(self, db: Session, id: int) -> Optional[DesignTool]:
        return crud_design_tool.get(db, id)

    def get_tool_by_code(self, db: Session, tool_code: str) -> Optional[DesignTool]:
        return crud_design_tool.get_by_tool_code(db, tool_code)

    def get_tools(
        self, db: Session, *, skip: int = 0, limit: int = 100, status: Optional[str] = None, design_type: Optional[str] = None, search: Optional[str] = None
    ) -> Tuple[List[DesignTool], int]:
        return crud_design_tool.get_multi(db, skip=skip, limit=limit, status=status, design_type=design_type, search=search)

    def create_tool(self, db: Session, tool_in: DesignToolCreate) -> DesignTool:
        """
        Business rule: tool_code must be unique - enforced at the DB level
        (UNIQUE constraint), surfaced here as a clear pre-check so the
        router can return a clean 400 rather than a raw IntegrityError.
        """
        existing = crud_design_tool.get_by_tool_code(db, tool_in.tool_code)
        if existing:
            raise ValueError(f"Tool code '{tool_in.tool_code}' already exists")
        return crud_design_tool.create(db, obj_in=tool_in)

    def update_tool(self, db: Session, id: int, tool_in: DesignToolUpdate) -> Optional[DesignTool]:
        """
        If tool_code is being changed, (tool_code) must remain unique
        across all other Tools - the current row is excluded from the
        collision check so re-saving a Tool with its own unchanged code
        never raises.
        """
        db_obj = crud_design_tool.get(db, id)
        if not db_obj:
            return None
        if tool_in.tool_code is not None and tool_in.tool_code != db_obj.tool_code:
            existing = crud_design_tool.get_by_tool_code(db, tool_in.tool_code)
            if existing and existing.id != id:
                raise ValueError(f"Tool code '{tool_in.tool_code}' already exists")
        return crud_design_tool.update(db, db_obj=db_obj, obj_in=tool_in)

    def delete_tool(self, db: Session, id: int) -> Optional[DesignTool]:
        """
        Business rule: a Tool may only be deleted where business rules
        permit - specifically, it must not be referenced by any existing
        Design Job. Deactivation (status='inactive'/'archived' via
        update_tool) is the correct action for retiring a Tool that has
        history; hard delete is reserved for Tools that were never used.
        """
        db_obj = crud_design_tool.get(db, id)
        if not db_obj:
            return None
        _, referenced_count = crud_design_job.get_multi(db, tool_id=id, limit=1)
        if referenced_count > 0:
            raise DesignToolReferencedError(
                f"Tool '{db_obj.tool_code}' cannot be deleted: it is referenced by {referenced_count} Design Job(s). "
                f"Set status to 'inactive' or 'archived' instead."
            )
        return crud_design_tool.remove(db, id=id)

design_tool_service = DesignToolService()

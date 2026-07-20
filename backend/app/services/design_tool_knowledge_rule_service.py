from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.crud.design_tool import design_tool as crud_design_tool
from app.crud.design_tool_knowledge_rule import design_tool_knowledge_rule as crud_design_tool_knowledge_rule
from app.schemas.design_tool_knowledge_rule import DesignToolKnowledgeRuleCreate, DesignToolKnowledgeRuleUpdate
from app.models.design_tool_knowledge_rule import DesignToolKnowledgeRule

_VALID_SCOPES = {"project", "property", "image"}

class DesignToolKnowledgeRuleService:
    def get_rule(self, db: Session, id: int) -> Optional[DesignToolKnowledgeRule]:
        return crud_design_tool_knowledge_rule.get(db, id)

    def get_rule_scoped(self, db: Session, *, tool_id: int, id: int) -> Optional[DesignToolKnowledgeRule]:
        """
        Ownership-scoped lookup: returns the Rule only if it both exists
        AND belongs to the given tool_id. Used by every nested GET/PUT/
        DELETE action - see DesignToolOptionService.get_option_scoped for
        the full rationale (applies identically here).
        """
        db_obj = crud_design_tool_knowledge_rule.get(db, id)
        if not db_obj or db_obj.tool_id != tool_id:
            return None
        return db_obj

    def get_rules(self, db: Session, *, skip: int = 0, limit: int = 100, tool_id: Optional[int] = None) -> Tuple[List[DesignToolKnowledgeRule], int]:
        return crud_design_tool_knowledge_rule.get_multi(db, skip=skip, limit=limit, tool_id=tool_id)

    def create_rule(self, db: Session, rule_in: DesignToolKnowledgeRuleCreate) -> DesignToolKnowledgeRule:
        """
        Business rules validated here (not in CRUD): the parent Tool must
        exist, knowledge_scope must be one of the three approved business
        scopes (project/property/image), and (tool_id, knowledge_scope)
        must be unique per the locked simplified structure.
        """
        tool = crud_design_tool.get(db, rule_in.tool_id)
        if not tool:
            raise ValueError(f"Tool {rule_in.tool_id} does not exist")
        if rule_in.knowledge_scope not in _VALID_SCOPES:
            raise ValueError(f"knowledge_scope must be one of {sorted(_VALID_SCOPES)}")
        existing = crud_design_tool_knowledge_rule.get_by_scope(db, tool_id=rule_in.tool_id, knowledge_scope=rule_in.knowledge_scope)
        if existing:
            raise ValueError(f"A knowledge rule for scope '{rule_in.knowledge_scope}' already exists for this Tool")
        return crud_design_tool_knowledge_rule.create(db, obj_in=rule_in)

    def update_rule(self, db: Session, *, tool_id: int, id: int, rule_in: DesignToolKnowledgeRuleUpdate) -> Optional[DesignToolKnowledgeRule]:
        """
        Ownership-checked update: the Rule must belong to tool_id or this
        returns None (router maps to 404). knowledge_scope is re-validated
        against the approved set if supplied, and if it is being changed,
        (tool_id, knowledge_scope) must remain unique among the Tool's
        other rules - the current row is excluded from the collision check.
        """
        db_obj = self.get_rule_scoped(db, tool_id=tool_id, id=id)
        if not db_obj:
            return None
        if rule_in.knowledge_scope is not None:
            if rule_in.knowledge_scope not in _VALID_SCOPES:
                raise ValueError(f"knowledge_scope must be one of {sorted(_VALID_SCOPES)}")
            if rule_in.knowledge_scope != db_obj.knowledge_scope:
                existing = crud_design_tool_knowledge_rule.get_by_scope(db, tool_id=tool_id, knowledge_scope=rule_in.knowledge_scope)
                if existing and existing.id != id:
                    raise ValueError(f"A knowledge rule for scope '{rule_in.knowledge_scope}' already exists for this Tool")
        return crud_design_tool_knowledge_rule.update(db, db_obj=db_obj, obj_in=rule_in)

    def delete_rule(self, db: Session, *, tool_id: int, id: int) -> Optional[DesignToolKnowledgeRule]:
        """Ownership-checked delete: the Rule must belong to tool_id or this returns None (router maps to 404)."""
        db_obj = self.get_rule_scoped(db, tool_id=tool_id, id=id)
        if not db_obj:
            return None
        return crud_design_tool_knowledge_rule.remove(db, id=id)

design_tool_knowledge_rule_service = DesignToolKnowledgeRuleService()

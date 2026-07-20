from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class DesignToolKnowledgeRuleBase(BaseModel):
    tool_id: int
    knowledge_scope: str  # project, property, image, design_job
    # Phase 1.2A - NULL means blanket scope rule (LEGACY_SCOPE_FIELDS);
    # a value must be a FIELD_RULE_REGISTRY code matching this scope.
    field_code: Optional[str] = None
    is_required: int = 0
    include_in_context: int = 1
    instructions: Optional[str] = None

class DesignToolKnowledgeRuleCreate(DesignToolKnowledgeRuleBase):
    pass

class DesignToolKnowledgeRuleUpdate(BaseModel):
    tool_id: Optional[int] = None
    knowledge_scope: Optional[str] = None
    field_code: Optional[str] = None
    is_required: Optional[int] = None
    include_in_context: Optional[int] = None
    instructions: Optional[str] = None

class DesignToolKnowledgeRuleRead(DesignToolKnowledgeRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

from sqlalchemy import Column, BigInteger, String, Text, Integer, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class DesignToolKnowledgeRule(Base):
    __tablename__ = "cre_design_tool_knowledge_rules"
    __table_args__ = (
        # Corrected in Phase 1.2A: the pre-1.2A constraint was
        # UNIQUE(tool_id, knowledge_scope) alone, which only ever allowed
        # exactly one rule row per scope per Tool - incompatible with
        # field-level rules, where a Tool may legitimately want several
        # rows in the same scope (e.g. both PROJECT.GOALS and
        # PROJECT.BUDGET). Adding field_code to the unique key allows
        # that. NULL is not equal to NULL under a unique index (MySQL/
        # MariaDB and SQLite both), so this alone would still permit more
        # than one field_code=NULL "blanket" row per (tool_id, scope) to
        # coexist - the service layer (knowledge_context_builder.py /
        # design_tool_knowledge_rule CRUD) additionally guards against
        # that case; this constraint is the second, DB-level layer, not
        # the only one.
        UniqueConstraint("tool_id", "knowledge_scope", "field_code", name="uq_design_tool_knowledge_rules_scope"),
    )

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    tool_id = Column(BigInteger, ForeignKey("cre_design_tools.id", ondelete="CASCADE"), nullable=False)
    knowledge_scope = Column(String(20), nullable=False)  # project, property, image, design_job
    # Phase 1.2A - additive, nullable. NULL means "blanket scope rule",
    # exactly as knowledge_scope alone meant before this phase (see
    # LEGACY_SCOPE_FIELDS in knowledge_context_builder.py for exactly
    # which fields that continues to produce). A non-null value must be
    # one of the codes in FIELD_RULE_REGISTRY and must match this row's
    # own knowledge_scope prefix; an unrecognized or mismatched value is
    # excluded from context assembly and logged, never raised, per the
    # approved architecture's "fail toward exclusion" policy.
    field_code = Column(String(100), nullable=True)
    is_required = Column(Integer, default=0, nullable=False)  # tinyint(1) DEFAULT '0'
    include_in_context = Column(Integer, default=1, nullable=False)  # tinyint(1) DEFAULT '1'
    instructions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    tool = relationship("DesignTool", back_populates="knowledge_rules")

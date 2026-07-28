-- =============================================================================
-- add_approved_baseline_active_scope_unique_constraint.sql
--
-- AIHOME Phase 1 - RC1 validation hotfix
--
-- ROOT CAUSE: app/models/approved_design_baseline.py's ApprovedDesignBaseline
-- model documents (in its own docstring) that active_scope_key carries a
-- UNIQUE constraint making it structurally impossible for two ACTIVE
-- baselines to exist for the same (property_id, design_type, design_scope)
-- - and the maintained SQL reference (ai_cre_schema.sql) already had this
-- constraint correctly - but the ORM model's __table_args__ never actually
-- declared it. Any database provisioned via Base.metadata.create_all()
-- (every test database used throughout this project) was missing this
-- DB-level backstop, relying solely on the application-level Property-row
-- lock in design_result_service.approve_design_version(). That lock is
-- itself correct and tested; this constraint is the documented,
-- intended defense-in-depth this table was designed to have from the start.
--
-- Additive only - one UNIQUE index on an existing generated column.
-- No data changes, no column changes. Idempotent: checks
-- INFORMATION_SCHEMA first, only adds the index if missing.
-- =============================================================================


-- SECTION 1 - PRE-MIGRATION VERIFICATION

SELECT VERSION();

-- Confirm the constraint is genuinely missing (expect ZERO rows).
SELECT TABLE_NAME, INDEX_NAME
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'cre_approved_design_baselines'
  AND INDEX_NAME = 'uq_approved_design_baselines_active_scope';

-- Diagnostic: confirm there is currently no genuine duplicate-active-scope
-- data that would make adding this constraint fail. Expect ZERO rows -
-- if this returns any, the migration cannot proceed until that data is
-- resolved manually (it would indicate the application-level lock had
-- already been bypassed somehow).
SELECT property_id, design_type, design_scope, COUNT(*) AS active_count
FROM cre_approved_design_baselines
WHERE status = 'active'
GROUP BY property_id, design_type, design_scope
HAVING COUNT(*) > 1;


-- SECTION 2 - MIGRATION

SET @idx_exists = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_approved_design_baselines'
    AND INDEX_NAME = 'uq_approved_design_baselines_active_scope'
);
SET @sql = IF(@idx_exists = 0,
  'ALTER TABLE cre_approved_design_baselines ADD UNIQUE KEY `uq_approved_design_baselines_active_scope` (`active_scope_key`)',
  'SELECT ''uq_approved_design_baselines_active_scope already exists, skipped'''
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- SECTION 3 - POST-MIGRATION VERIFICATION

SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'cre_approved_design_baselines'
  AND INDEX_NAME = 'uq_approved_design_baselines_active_scope';
-- Expect exactly one row, NON_UNIQUE = 0.

SELECT COUNT(*) AS row_count FROM cre_approved_design_baselines;
-- Compare against a pre-migration count taken separately - row count must
-- be unchanged (this migration never touches data).


-- SECTION 4 - ROLLBACK (only if genuinely needed)

-- ALTER TABLE cre_approved_design_baselines DROP INDEX `uq_approved_design_baselines_active_scope`;

-- =============================================================================
-- END OF FILE
-- =============================================================================

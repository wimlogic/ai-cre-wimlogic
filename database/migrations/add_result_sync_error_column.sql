-- =============================================================================
-- add_result_sync_error_column.sql
--
-- AI-CRE / AI HOME WIMLOGIC - hotfix migration
--
-- ROOT CAUSE: app/models/workflow_execution.py's WorkflowExecution ORM
-- model has a `result_sync_error` column (Text, nullable) added during
-- the "Render Completed DEV-TOOLS Output as Natural-Language Report"
-- phase - but that phase produced no dedicated ALTER migration file for
-- it (unlike the later Knowledge Inheritance Phase 1.2A work, which
-- explicitly did). The column exists only in the Python model and in
-- databases built fresh via SQLAlchemy's Base.metadata.create_all() -
-- never in a database provisioned from the maintained SQL reference
-- dump, and never via an explicit ALTER against an already-running
-- database. This live instance is exactly that case: the ORM issues
-- `SELECT ... cre_workflow_executions.result_sync_error ...` on every
-- query against this table (it's a real column in the model, so
-- SQLAlchemy always includes it), and the live table doesn't have it -
-- hence "Unknown column 'cre_workflow_executions.result_sync_error' in
-- 'field list'" on every attempted submission, not just this one.
--
-- Also confirmed: the maintained ai_cre_schema.sql reference file is
-- ALSO missing this column (checked directly) - this is corrected
-- separately, alongside this migration, for consistency.
--
-- DOES NOT DROP OR RECREATE ANY TABLE. One additive nullable column.
-- Idempotent: checks INFORMATION_SCHEMA first, only runs the ALTER if
-- the column doesn't already exist, so this is safe to run more than
-- once and safe to run alongside a fresh deployment that already has it.
--
-- Tested end-to-end against a real MySQL 8.0.46 instance (see delivery
-- notes for full first/second-run output) - not executed against this
-- live/production database.
-- =============================================================================


-- SECTION 1 - PRE-MIGRATION VERIFICATION

-- 1a. Confirm the server version.
SELECT VERSION();

-- 1b. Confirm the column is actually missing (expect ZERO rows back -
--     if this returns a row, the column already exists and the ALTER
--     below will correctly no-op).
SELECT TABLE_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'cre_workflow_executions'
  AND COLUMN_NAME = 'result_sync_error';

-- 1c. Row-count baseline, to confirm after migration that no rows were
--     added, removed, or lost.
SELECT COUNT(*) AS row_count FROM cre_workflow_executions;


-- SECTION 2 - MIGRATION

SET @col_exists = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_workflow_executions'
    AND COLUMN_NAME = 'result_sync_error'
);
SET @sql = IF(@col_exists = 0,
  'ALTER TABLE cre_workflow_executions ADD COLUMN `result_sync_error` text NULL',
  'SELECT ''cre_workflow_executions.result_sync_error already exists, skipped'''
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- SECTION 3 - POST-MIGRATION VERIFICATION

-- 3a. Column now present.
SELECT TABLE_NAME, COLUMN_NAME, IS_NULLABLE, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'cre_workflow_executions'
  AND COLUMN_NAME = 'result_sync_error';
-- Expect exactly one row, IS_NULLABLE = 'YES'.

-- 3b. Row count unchanged - compare against Section 1c.
SELECT COUNT(*) AS row_count FROM cre_workflow_executions;

-- 3c. Every existing row's new column is NULL (no default was silently
--     backfilled).
SELECT execution_id, result_sync_error FROM cre_workflow_executions ORDER BY execution_id LIMIT 5;

-- =============================================================================
-- END OF FILE
-- =============================================================================

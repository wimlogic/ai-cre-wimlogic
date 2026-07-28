-- =============================================================================
-- add_additional_business_intents_column.sql
--
-- AIHOME RC2 - WACP 1.1 / WIM Module V2 platform integration.
--
-- Adds ONE nullable JSON column to cre_workflow_executions:
-- additional_business_intents - AIHOME's own audit record of the ordered
-- follow-on Business Intents requested alongside an execution's primary
-- business_intent (WACP 1.1's additional_business_intents field). NULL
-- for every WACP 1.0 single-intent execution, which is the overwhelming
-- majority and is completely unaffected by this migration.
--
-- This is NOT the same column as DEV-TOOLS' own intent_execution_plan -
-- that lives entirely on the DEV-TOOLS side (WIM Module V2's own
-- resolution decision) and AIHOME never receives or stores it. This
-- column only records what AIHOME itself requested.
--
-- Additive only. No data changes to any existing row. Idempotent -
-- checks INFORMATION_SCHEMA first, only adds the column if missing.
-- =============================================================================


-- SECTION 1 - PRE-MIGRATION VERIFICATION

SELECT VERSION();

-- Confirm the column is genuinely missing (expect ZERO rows).
SELECT TABLE_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'cre_workflow_executions'
  AND COLUMN_NAME = 'additional_business_intents';

-- Confirm current row count for the before/after comparison in Section 3.
SELECT COUNT(*) AS row_count_before FROM cre_workflow_executions;


-- SECTION 2 - MIGRATION

SET @col_exists = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_workflow_executions'
    AND COLUMN_NAME = 'additional_business_intents'
);
SET @sql = IF(@col_exists = 0,
  'ALTER TABLE cre_workflow_executions ADD COLUMN `additional_business_intents` JSON NULL AFTER `metadata_json`',
  'SELECT ''additional_business_intents already exists, skipped'''
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- SECTION 3 - POST-MIGRATION VERIFICATION

SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'cre_workflow_executions'
  AND COLUMN_NAME = 'additional_business_intents';
-- Expect exactly one row: DATA_TYPE = 'json', IS_NULLABLE = 'YES'.

SELECT COUNT(*) AS row_count_after FROM cre_workflow_executions;
-- Must be unchanged from Section 1's row_count_before - this migration
-- never touches existing data.


-- SECTION 4 - ROLLBACK (only if genuinely needed)

-- ALTER TABLE cre_workflow_executions DROP COLUMN `additional_business_intents`;

-- =============================================================================
-- END OF FILE
-- =============================================================================

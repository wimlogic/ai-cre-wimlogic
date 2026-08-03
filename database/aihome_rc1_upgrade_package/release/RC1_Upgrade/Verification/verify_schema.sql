-- =============================================================================
-- verify_schema.sql — AIHOME Community Edition v1.0 RC1
-- Schema verification for an upgraded (existing) AIHOME database.
--
-- Run against the target database. Every check states its EXPECTED result
-- inline. All expected results are also listed in Deploy_RC1.md.
-- =============================================================================

-- CHECK 1: RC1 Design Studio tables exist.
-- EXPECTED: table_count = 3
SELECT COUNT(*) AS table_count
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN ('cre_design_image_versions',
                     'cre_design_image_lineage',
                     'cre_approved_design_baselines');

-- CHECK 2: active_scope_key generated column exists exactly once.
-- EXPECTED: 1 row; EXTRA contains 'STORED GENERATED'
SELECT COLUMN_NAME, EXTRA
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'cre_approved_design_baselines'
  AND column_name = 'active_scope_key';

-- CHECK 3: the one-active-baseline-per-scope UNIQUE constraint exists.
-- EXPECTED: 1 row; NON_UNIQUE = 0
SELECT INDEX_NAME, NON_UNIQUE
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'cre_approved_design_baselines'
  AND column_name = 'active_scope_key'
  AND non_unique = 0
GROUP BY INDEX_NAME, NON_UNIQUE;

-- CHECK 4: result_sync_error column present on cre_workflow_executions.
-- EXPECTED: 1 row; DATA_TYPE = 'text'; IS_NULLABLE = 'YES'
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'cre_workflow_executions'
  AND column_name = 'result_sync_error';

-- CHECK 5: per-job monotonic version uniqueness constraint
-- (design_job_id, version_number) is UNIQUE on cre_design_image_versions.
-- EXPECTED: 1 row; cols = 'design_job_id,version_number'
SELECT INDEX_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS cols
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'cre_design_image_versions'
  AND non_unique = 0
  AND index_name <> 'PRIMARY'
GROUP BY INDEX_NAME
HAVING cols = 'design_job_id,version_number';

-- CHECK 6: lineage table FKs intact (version, property-image source,
-- version source).
-- EXPECTED: fk_count = 3
SELECT COUNT(*) AS fk_count
FROM information_schema.key_column_usage
WHERE table_schema = DATABASE()
  AND table_name = 'cre_design_image_lineage'
  AND referenced_table_name IS NOT NULL;

-- CHECK 7: no duplicate index definitions (two indexes covering the same
-- ordered column set) on the three RC1 tables.
-- EXPECTED: zero rows
SELECT table_name, cols, COUNT(*) AS duplicate_indexes
FROM (
  SELECT table_name, index_name,
         GROUP_CONCAT(column_name ORDER BY seq_in_index) AS cols
  FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name IN ('cre_design_image_versions',
                       'cre_design_image_lineage',
                       'cre_approved_design_baselines')
  GROUP BY table_name, index_name
) AS per_index
GROUP BY table_name, cols
HAVING COUNT(*) > 1;

-- CHECK 8: no duplicate generated columns anywhere in the schema
-- (exactly one is expected in the entire database: active_scope_key).
-- EXPECTED: 1 row: cre_approved_design_baselines / active_scope_key
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND generation_expression <> '';

-- CHECK 9: no triggers exist (none are part of any AIHOME release).
-- EXPECTED: trigger_count = 0
SELECT COUNT(*) AS trigger_count
FROM information_schema.triggers
WHERE trigger_schema = DATABASE();

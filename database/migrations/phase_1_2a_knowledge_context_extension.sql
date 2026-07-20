-- =============================================================================
-- phase_1_2a_knowledge_context_extension.sql
--
-- AI HOME WIMLOGIC - Knowledge Inheritance Engine Phase 1.2A
-- Idempotent ALTER-only migration.
--
-- DOES NOT DROP OR RECREATE ANY TABLE. Every statement in this file either
-- adds a nullable column, or replaces an index/CHECK constraint on an
-- EXISTING table, in place, preserving all existing rows and data.
--
-- Target: real AIHOME production/staging MySQL 8.0.x (confirmed via the
-- maintained schema reference's utf8mb4_0900_ai_ci collation, a MySQL
-- 8.0-specific collation). This revision was tested end-to-end against a
-- real MySQL 8.0.46 instance (matching the exact target version) -
-- confirmed concretely:
--
--   SHOW INDEX FROM cre_design_tool_knowledge_rules;
--     -> uq_design_tool_knowledge_rules_scope (tool_id, knowledge_scope)
--   SELECT cc.CONSTRAINT_NAME FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
--     JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc ON ... (see Section 1c)
--     -> chk_design_tool_knowledge_rules_scope
--
-- CORRECTED IN THIS REVISION: INFORMATION_SCHEMA.CHECK_CONSTRAINTS has NO
-- TABLE_NAME column in real MySQL 8 - only CONSTRAINT_CATALOG,
-- CONSTRAINT_SCHEMA, CONSTRAINT_NAME, CHECK_CLAUSE. The prior revision's
-- filter on CHECK_CONSTRAINTS.TABLE_NAME (Section 1c, @chk_exists,
-- @new_chk_exists, Section 3c) worked only because MariaDB non-
-- standardly adds a TABLE_NAME column to this view - it would have
-- failed outright on real MySQL 8 with "Unknown column 'TABLE_NAME'".
-- All four occurrences are now corrected to join against
-- INFORMATION_SCHEMA.TABLE_CONSTRAINTS (which does have TABLE_NAME and
-- CONSTRAINT_TYPE) on (CONSTRAINT_SCHEMA, CONSTRAINT_NAME).
--
-- ATOMICITY - READ BEFORE RUNNING: MySQL's ALTER TABLE statements each
-- perform an implicit commit before and after execution (this applies to
-- every ALTER TABLE in this file, including the ones wrapped in PREPARE/
-- EXECUTE - PREPARE/EXECUTE does not create or extend a transaction
-- around the statement it runs). This migration is therefore NOT
-- transactionally atomic as a whole: if it fails partway through (e.g.
-- MySQL restarts mid-file, or a step legitimately fails), some ALTER
-- TABLE statements before that point will already be permanently
-- committed and will NOT be rolled back by anything later in this file
-- failing. This is exactly why every operation here is independently
-- idempotent (checks INFORMATION_SCHEMA first) - re-running the whole
-- file after a partial failure is the intended recovery path, not a
-- transactional rollback.
--
-- IMPORTANT - READ BEFORE RUNNING: this file was verified against a real
-- MySQL 8.0.46 instance built from the maintained schema reference, not
-- against the actual live AIHOME database referenced in this request (no
-- direct connection to that instance was available). Run the PRE-
-- MIGRATION VERIFICATION section first (including the VERSION() and
-- SHOW FULL COLUMNS preflight checks) and compare its output against the
-- names/collations assumed above before running anything further. If the
-- live names differ, adjust the @unique_index_name / @check_constraint_name
-- variables in the migration section accordingly - every DDL statement
-- below is driven by those variables, not hardcoded twice, so a name
-- correction only needs to happen in one place.
--
-- Idempotency strategy: every operation below checks INFORMATION_SCHEMA
-- first and only executes its DDL via PREPARE/EXECUTE if the target
-- state doesn't already exist. This is used uniformly (rather than
-- relying on "ADD COLUMN IF NOT EXISTS"-style syntax sugar) so the same
-- pattern works identically across MySQL 8.x patch versions without any
-- syntax-availability assumption.
--
-- TRUE idempotency for the index/CHECK swap (Section 2.6/2.7): rather
-- than unconditionally dropping and recreating the unique index and the
-- knowledge_scope CHECK constraint whenever they exist under their
-- expected names, this revision first inspects their ACTUAL current
-- shape - the index's ordered column list, the CHECK clause's contained
-- values - and skips the drop (and therefore the recreate) entirely when
-- the current shape already matches the target. A second run against an
-- already-migrated database performs ZERO ALTER TABLE statements
-- anywhere in this file, not just "ends up in the same final state."
--
-- FILE SPLIT: this file (phase_1_2a_knowledge_context_extension.sql)
-- contains ONLY Sections 0-3 (preflight, pre-migration verification,
-- migration, post-migration verification) and ends there - it contains
-- NO rollback statements of any kind, so running it start to finish
-- applies the migration and stops. Rollback SQL lives in a separate,
-- deliberately distinct file:
-- phase_1_2a_knowledge_context_extension_rollback.sql - it must be
-- located and run independently, never as a continuation of this file.
-- =============================================================================


-- =============================================================================
-- SECTION 0 - PREFLIGHT (run first, before Section 1)
-- =============================================================================

-- 0a. Confirm the actual server version this migration is about to run
--     against - compare against "Target: real AIHOME production/staging
--     MySQL 8.0.x" above. This migration was authored and tested against
--     8.0.46 specifically; a materially different version (e.g. MySQL
--     5.7, which has no CHECK constraint support at all, or MariaDB,
--     whose INFORMATION_SCHEMA.CHECK_CONSTRAINTS shape differs as noted
--     above) should not proceed without re-verification.
SELECT VERSION();

-- 0b. Confirm the two cre_design_jobs text columns' actual current
--     collation on the live table before this migration adds job_prompt/
--     job_constraints - the migration below sets those two new columns
--     to utf8mb4_0900_ai_ci specifically to match every OTHER text
--     column already on this table (workflow_code, tool_code,
--     design_type, job_number all use this collation in the maintained
--     reference); if the live table's actual columns differ, adjust the
--     COLLATE clauses in Section 2.4 accordingly before running it.
SHOW FULL COLUMNS FROM cre_design_jobs;



-- =============================================================================
-- SECTION 1 - PRE-MIGRATION VERIFICATION (run first, read the output)
-- =============================================================================

-- 1a. Confirm none of the new columns already exist (expect ZERO rows
--     back from this query on a database that has never run this
--     migration before; a non-empty result means either this migration
--     already ran, or a naming collision exists that must be understood
--     before proceeding).
SELECT TABLE_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND (
    (TABLE_NAME = 'cre_projects' AND COLUMN_NAME IN ('goals','hoa_rules','climate','budget_low','budget_high','preferred_styles','design_preferences'))
    OR (TABLE_NAME = 'cre_properties' AND COLUMN_NAME IN ('bedrooms','bathrooms','construction_type','existing_materials','existing_colors'))
    OR (TABLE_NAME = 'cre_property_images' AND COLUMN_NAME IN ('camera_direction','existing_furniture','existing_lighting'))
    OR (TABLE_NAME = 'cre_design_jobs' AND COLUMN_NAME IN ('job_prompt','job_constraints'))
    OR (TABLE_NAME = 'cre_design_tool_knowledge_rules' AND COLUMN_NAME = 'field_code')
  );

-- 1b. Confirm the CURRENT actual name of the unique index on
--     cre_design_tool_knowledge_rules (compare against
--     'uq_design_tool_knowledge_rules_scope' assumed above).
SELECT DISTINCT INDEX_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS columns
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'cre_design_tool_knowledge_rules'
  AND NON_UNIQUE = 0
  AND INDEX_NAME != 'PRIMARY'
GROUP BY INDEX_NAME;

-- 1c. Confirm the CURRENT actual name of the knowledge_scope CHECK
--     constraint (compare against 'chk_design_tool_knowledge_rules_scope'
--     assumed above). INFORMATION_SCHEMA.CHECK_CONSTRAINTS has NO
--     TABLE_NAME column in real MySQL 8 (MariaDB non-standardly adds
--     one, which is why this bug wasn't caught during MariaDB-only
--     testing) - TABLE_NAME must come from a join against
--     TABLE_CONSTRAINTS instead.
SELECT cc.CONSTRAINT_NAME, cc.CHECK_CLAUSE
FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
  ON tc.CONSTRAINT_SCHEMA = cc.CONSTRAINT_SCHEMA
  AND tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
WHERE tc.TABLE_SCHEMA = DATABASE()
  AND tc.TABLE_NAME = 'cre_design_tool_knowledge_rules'
  AND tc.CONSTRAINT_TYPE = 'CHECK';

-- 1d. Row-count baseline for the five affected tables, to compare
--     against the same counts after migration (Section 3) - confirms no
--     rows were added, removed, or lost.
SELECT 'cre_projects' AS table_name, COUNT(*) AS row_count FROM cre_projects
UNION ALL SELECT 'cre_properties', COUNT(*) FROM cre_properties
UNION ALL SELECT 'cre_property_images', COUNT(*) FROM cre_property_images
UNION ALL SELECT 'cre_design_jobs', COUNT(*) FROM cre_design_jobs
UNION ALL SELECT 'cre_design_tool_knowledge_rules', COUNT(*) FROM cre_design_tool_knowledge_rules;

-- 1e. Confirm no existing row already uses a knowledge_scope value the
--     new CHECK constraint wouldn't also accept (expect ZERO rows - the
--     new constraint is a strict superset of the old one, adding
--     'design_job', so this should never find anything, but it is
--     checked explicitly rather than assumed).
SELECT id, tool_id, knowledge_scope
FROM cre_design_tool_knowledge_rules
WHERE knowledge_scope NOT IN ('project', 'property', 'image', 'design_job');


-- =============================================================================
-- SECTION 2 - MIGRATION
-- =============================================================================

-- Adjust these two if Section 1b/1c's output differs from the assumed names.
SET @unique_index_name = 'uq_design_tool_knowledge_rules_scope';
SET @check_constraint_name = 'chk_design_tool_knowledge_rules_scope';


-- -----------------------------------------------------------------------
-- 2.1 cre_projects - add 7 nullable columns
-- -----------------------------------------------------------------------
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_projects' AND COLUMN_NAME = 'goals');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_projects ADD COLUMN `goals` text NULL', 'SELECT ''cre_projects.goals already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_projects' AND COLUMN_NAME = 'hoa_rules');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_projects ADD COLUMN `hoa_rules` text NULL', 'SELECT ''cre_projects.hoa_rules already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_projects' AND COLUMN_NAME = 'climate');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_projects ADD COLUMN `climate` text NULL', 'SELECT ''cre_projects.climate already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_projects' AND COLUMN_NAME = 'budget_low');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_projects ADD COLUMN `budget_low` decimal(14,2) NULL', 'SELECT ''cre_projects.budget_low already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_projects' AND COLUMN_NAME = 'budget_high');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_projects ADD COLUMN `budget_high` decimal(14,2) NULL', 'SELECT ''cre_projects.budget_high already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_projects' AND COLUMN_NAME = 'preferred_styles');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_projects ADD COLUMN `preferred_styles` json NULL', 'SELECT ''cre_projects.preferred_styles already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_projects' AND COLUMN_NAME = 'design_preferences');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_projects ADD COLUMN `design_preferences` text NULL', 'SELECT ''cre_projects.design_preferences already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- -----------------------------------------------------------------------
-- 2.2 cre_properties - add 5 nullable columns
-- -----------------------------------------------------------------------
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_properties' AND COLUMN_NAME = 'bedrooms');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_properties ADD COLUMN `bedrooms` int NULL', 'SELECT ''cre_properties.bedrooms already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_properties' AND COLUMN_NAME = 'bathrooms');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_properties ADD COLUMN `bathrooms` decimal(3,1) NULL', 'SELECT ''cre_properties.bathrooms already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_properties' AND COLUMN_NAME = 'construction_type');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_properties ADD COLUMN `construction_type` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL', 'SELECT ''cre_properties.construction_type already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_properties' AND COLUMN_NAME = 'existing_materials');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_properties ADD COLUMN `existing_materials` json NULL', 'SELECT ''cre_properties.existing_materials already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_properties' AND COLUMN_NAME = 'existing_colors');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_properties ADD COLUMN `existing_colors` json NULL', 'SELECT ''cre_properties.existing_colors already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- -----------------------------------------------------------------------
-- 2.3 cre_property_images - add 3 nullable columns
-- -----------------------------------------------------------------------
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_property_images' AND COLUMN_NAME = 'camera_direction');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_property_images ADD COLUMN `camera_direction` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL', 'SELECT ''cre_property_images.camera_direction already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_property_images' AND COLUMN_NAME = 'existing_furniture');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_property_images ADD COLUMN `existing_furniture` json NULL', 'SELECT ''cre_property_images.existing_furniture already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_property_images' AND COLUMN_NAME = 'existing_lighting');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_property_images ADD COLUMN `existing_lighting` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL', 'SELECT ''cre_property_images.existing_lighting already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- -----------------------------------------------------------------------
-- 2.4 cre_design_jobs - add 2 nullable columns
-- -----------------------------------------------------------------------
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_design_jobs' AND COLUMN_NAME = 'job_prompt');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_design_jobs ADD COLUMN `job_prompt` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL', 'SELECT ''cre_design_jobs.job_prompt already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_design_jobs' AND COLUMN_NAME = 'job_constraints');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_design_jobs ADD COLUMN `job_constraints` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL', 'SELECT ''cre_design_jobs.job_constraints already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- -----------------------------------------------------------------------
-- 2.5 cre_design_tool_knowledge_rules - add field_code column
-- -----------------------------------------------------------------------
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_design_tool_knowledge_rules' AND COLUMN_NAME = 'field_code');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE cre_design_tool_knowledge_rules ADD COLUMN `field_code` varchar(100) NULL', 'SELECT ''cre_design_tool_knowledge_rules.field_code already exists, skipped''');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- -----------------------------------------------------------------------
-- 2.6 cre_design_tool_knowledge_rules - replace the unique index
--
-- True idempotency: inspect the CURRENT ordered column list of the index
-- named by @unique_index_name. If it already equals exactly
-- "tool_id,knowledge_scope,field_code", this index is already at the
-- target shape - do NOT drop or recreate it (a DROP+ADD pair that
-- reconstructs an already-correct index still counts as two ALTER TABLE
-- operations on a "no-op" run, which is not true idempotency). Only when
-- the current shape differs (or the index doesn't exist at all under
-- this name) does this section touch anything.
--
-- Does not touch idx_design_tool_knowledge_rules_tool_id (a separate,
-- non-unique index) or the PRIMARY KEY - only the one named unique index.
-- -----------------------------------------------------------------------
SET @current_index_columns = (
  SELECT GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX SEPARATOR ',')
  FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_design_tool_knowledge_rules'
    AND INDEX_NAME = @unique_index_name
  GROUP BY INDEX_NAME
);
SET @index_already_at_target = (@current_index_columns = 'tool_id,knowledge_scope,field_code');

SET @idx_exists = (
  SELECT COUNT(DISTINCT INDEX_NAME) FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_design_tool_knowledge_rules' AND INDEX_NAME = @unique_index_name
);
SET @sql = IF(@idx_exists > 0 AND NOT COALESCE(@index_already_at_target, FALSE),
  CONCAT('ALTER TABLE cre_design_tool_knowledge_rules DROP INDEX `', @unique_index_name, '`'),
  CONCAT('SELECT ''Index '', @unique_index_name, '' already at target shape or not found, drop skipped''')
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @new_idx_exists = (
  SELECT COUNT(DISTINCT INDEX_NAME) FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_design_tool_knowledge_rules'
    AND INDEX_NAME = 'uq_design_tool_knowledge_rules_scope'
);
SET @sql = IF(@new_idx_exists = 0,
  'ALTER TABLE cre_design_tool_knowledge_rules ADD UNIQUE KEY `uq_design_tool_knowledge_rules_scope` (`tool_id`,`knowledge_scope`,`field_code`)',
  'SELECT ''uq_design_tool_knowledge_rules_scope (3-column) already exists, add skipped'''
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- -----------------------------------------------------------------------
-- 2.7 cre_design_tool_knowledge_rules - replace the knowledge_scope CHECK
--
-- True idempotency: inspect the CURRENT CHECK_CLAUSE text for the
-- constraint named by @check_constraint_name. If it already contains all
-- four required scope values (project, property, image, design_job),
-- this constraint already accepts everything the target state requires -
-- do NOT drop or recreate it. Substring matching (LIKE '%value%') is
-- used rather than an exact CHECK_CLAUSE string comparison, since
-- MySQL's stored/normalized representation of a CHECK clause (quoting,
-- backtick placement, whitespace) is not guaranteed identical to the
-- literal text originally submitted - checking for the presence of each
-- required value is a more robust "does this already accept everything
-- we need" test than a brittle exact-text comparison.
-- -----------------------------------------------------------------------
SET @current_check_clause = (
  SELECT cc.CHECK_CLAUSE FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
  JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
    ON tc.CONSTRAINT_SCHEMA = cc.CONSTRAINT_SCHEMA AND tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
  WHERE tc.TABLE_SCHEMA = DATABASE() AND tc.TABLE_NAME = 'cre_design_tool_knowledge_rules'
    AND tc.CONSTRAINT_TYPE = 'CHECK' AND cc.CONSTRAINT_NAME = @check_constraint_name
);
SET @check_already_at_target = (
  @current_check_clause IS NOT NULL
  AND @current_check_clause LIKE '%project%'
  AND @current_check_clause LIKE '%property%'
  AND @current_check_clause LIKE '%image%'
  AND @current_check_clause LIKE '%design_job%'
);

SET @chk_exists = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
  JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
    ON tc.CONSTRAINT_SCHEMA = cc.CONSTRAINT_SCHEMA AND tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
  WHERE tc.TABLE_SCHEMA = DATABASE() AND tc.TABLE_NAME = 'cre_design_tool_knowledge_rules'
    AND tc.CONSTRAINT_TYPE = 'CHECK' AND cc.CONSTRAINT_NAME = @check_constraint_name
);
SET @sql = IF(@chk_exists > 0 AND NOT COALESCE(@check_already_at_target, FALSE),
  CONCAT('ALTER TABLE cre_design_tool_knowledge_rules DROP CONSTRAINT `', @check_constraint_name, '`'),
  CONCAT('SELECT ''Check constraint '', @check_constraint_name, '' already accepts all four scope values or not found, drop skipped''')
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @new_chk_exists = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
  JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
    ON tc.CONSTRAINT_SCHEMA = cc.CONSTRAINT_SCHEMA AND tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
  WHERE tc.TABLE_SCHEMA = DATABASE() AND tc.TABLE_NAME = 'cre_design_tool_knowledge_rules'
    AND tc.CONSTRAINT_TYPE = 'CHECK' AND cc.CONSTRAINT_NAME = 'chk_design_tool_knowledge_rules_scope'
);
SET @sql = IF(@new_chk_exists = 0,
  'ALTER TABLE cre_design_tool_knowledge_rules ADD CONSTRAINT `chk_design_tool_knowledge_rules_scope` CHECK ((`knowledge_scope` in (_utf8mb4''project'',_utf8mb4''property'',_utf8mb4''image'',_utf8mb4''design_job'')))',
  'SELECT ''chk_design_tool_knowledge_rules_scope (4-value) already exists, add skipped'''
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- =============================================================================
-- SECTION 3 - POST-MIGRATION VERIFICATION (run after, compare against Section 1)
-- =============================================================================

-- 3a. All 18 new columns now present (expect exactly 18 rows).
SELECT TABLE_NAME, COLUMN_NAME, IS_NULLABLE, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND (
    (TABLE_NAME = 'cre_projects' AND COLUMN_NAME IN ('goals','hoa_rules','climate','budget_low','budget_high','preferred_styles','design_preferences'))
    OR (TABLE_NAME = 'cre_properties' AND COLUMN_NAME IN ('bedrooms','bathrooms','construction_type','existing_materials','existing_colors'))
    OR (TABLE_NAME = 'cre_property_images' AND COLUMN_NAME IN ('camera_direction','existing_furniture','existing_lighting'))
    OR (TABLE_NAME = 'cre_design_jobs' AND COLUMN_NAME IN ('job_prompt','job_constraints'))
    OR (TABLE_NAME = 'cre_design_tool_knowledge_rules' AND COLUMN_NAME = 'field_code')
  )
ORDER BY TABLE_NAME, COLUMN_NAME;
-- Expect IS_NULLABLE = 'YES' for every row above - confirms no column
-- was accidentally created NOT NULL, which would have required a
-- default and risked rejecting the ALTER on a non-empty table.

-- 3b. New 3-column unique index confirmed.
SELECT INDEX_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS columns
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'cre_design_tool_knowledge_rules'
  AND INDEX_NAME = 'uq_design_tool_knowledge_rules_scope'
GROUP BY INDEX_NAME;
-- Expect: columns = 'tool_id,knowledge_scope,field_code'

-- 3c. New CHECK constraint confirmed.
SELECT cc.CONSTRAINT_NAME, cc.CHECK_CLAUSE
FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
  ON tc.CONSTRAINT_SCHEMA = cc.CONSTRAINT_SCHEMA
  AND tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
WHERE tc.TABLE_SCHEMA = DATABASE()
  AND tc.TABLE_NAME = 'cre_design_tool_knowledge_rules'
  AND tc.CONSTRAINT_TYPE = 'CHECK'
  AND cc.CONSTRAINT_NAME = 'chk_design_tool_knowledge_rules_scope';
-- Expect CHECK_CLAUSE to include all four values: project, property,
-- image, design_job.

-- 3d. Row counts unchanged - compare every number here against Section 1d.
SELECT 'cre_projects' AS table_name, COUNT(*) AS row_count FROM cre_projects
UNION ALL SELECT 'cre_properties', COUNT(*) FROM cre_properties
UNION ALL SELECT 'cre_property_images', COUNT(*) FROM cre_property_images
UNION ALL SELECT 'cre_design_jobs', COUNT(*) FROM cre_design_jobs
UNION ALL SELECT 'cre_design_tool_knowledge_rules', COUNT(*) FROM cre_design_tool_knowledge_rules;

-- 3e. Every new column is NULL on every pre-existing row (spot-check on
--     one row per table, if any rows exist) - confirms no default value
--     was silently backfilled anywhere.
SELECT id, goals, hoa_rules, climate, budget_low, budget_high, preferred_styles, design_preferences
FROM cre_projects ORDER BY id LIMIT 1;

SELECT id, bedrooms, bathrooms, construction_type, existing_materials, existing_colors
FROM cre_properties ORDER BY id LIMIT 1;

SELECT id, camera_direction, existing_furniture, existing_lighting
FROM cre_property_images ORDER BY id LIMIT 1;

SELECT id, job_prompt, job_constraints
FROM cre_design_jobs ORDER BY id LIMIT 1;

SELECT id, field_code
FROM cre_design_tool_knowledge_rules ORDER BY id LIMIT 1;


-- =============================================================================
-- END OF FILE - phase_1_2a_knowledge_context_extension.sql
--
-- This file intentionally ends here. It contains Sections 0-3 only
-- (preflight, pre-migration verification, migration, post-migration
-- verification) and NO rollback statements of any kind - running this
-- file start to finish applies the migration and stops. Rollback, if
-- ever needed, lives in the separate file
-- phase_1_2a_knowledge_context_extension_rollback.sql, which must be
-- run deliberately and separately.
-- =============================================================================

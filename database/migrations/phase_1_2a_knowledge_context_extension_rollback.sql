-- =============================================================================
-- phase_1_2a_knowledge_context_extension_rollback.sql
--
-- AI HOME WIMLOGIC - Knowledge Inheritance Engine Phase 1.2A
-- ROLLBACK for phase_1_2a_knowledge_context_extension.sql.
--
-- THIS FILE IS SEPARATE AND STANDALONE ON PURPOSE. It is not a
-- continuation of, or appended to, the main migration file - the two
-- must never be concatenated or run as one script. Run this file only
-- when a deliberate decision has been made to revert Phase 1.2A.
--
-- DESTRUCTIVE - READ BEFORE RUNNING: the column drops in this file are
-- safe ONLY if no application has yet written real data into any of the
-- 18 Phase 1.2A columns since the migration ran - DROP COLUMN is
-- destructive and irreversible. If Phase 1.2A backend code has already
-- gone live and any Tool has started using field-level Knowledge Rules,
-- or any of these fields have been populated on real Project/Property/
-- Image/Design Job rows, back up that data before rolling back, or do
-- not roll back at all.
--
-- ATOMICITY: exactly as in the main migration file, every ALTER TABLE
-- statement below implicitly commits in MySQL - this rollback is not
-- transactionally atomic. Run the diagnostic queries (4.1) first and
-- resolve anything they flag before proceeding; do not run this file
-- speculatively.
--
-- Target: MySQL 8.0.x, tested end-to-end against a real MySQL 8.0.46
-- instance (see delivery notes for full first/second-run output).
-- =============================================================================


-- =============================================================================
-- SECTION 4 - ROLLBACK SQL (where safely possible)
--
-- Read before running: the column drops below are safe ONLY if no
-- application has yet written real data into any of these 18 new
-- columns since this migration ran - DROP COLUMN is destructive and
-- irreversible. If Phase 1.2A backend code has already gone live and
-- any Tool has started using field-level Knowledge Rules or any of
-- these fields have been populated on real Project/Property/Image/
-- Design Job rows, back up that data before rolling back, or do not
-- roll back at all.
--
-- The CHECK constraint rollback (4.3) will FAIL if any row already has
-- knowledge_scope = 'design_job' - that is intentional: reverting to a
-- constraint that would make existing data invalid must not happen
-- silently. Remove or re-scope those rows first if rollback is genuinely
-- required after design_job rules have been created.
-- =============================================================================

-- 4.1 Diagnostic queries - RUN THESE FIRST, before anything else in this
--     section. They tell you whether 4.2/4.4 below are even safe to run.
SELECT tool_id, knowledge_scope, COUNT(*) AS row_count
FROM cre_design_tool_knowledge_rules
GROUP BY tool_id, knowledge_scope
HAVING COUNT(*) > 1;
-- Any row returned above means 4.2 (reverting to the 2-column unique
-- index) will fail with a duplicate-key error until those extra rows
-- are removed or consolidated - this is expected and correct: the whole
-- point of Phase 1.2A's index change was to allow this.

SELECT id, tool_id, field_code
FROM cre_design_tool_knowledge_rules
WHERE knowledge_scope = 'design_job';
-- Any row returned above means 4.4 (reverting the CHECK constraint to
-- its original 3-value form) will fail until these rows are removed or
-- re-scoped - reverting to a constraint that would make existing data
-- invalid must not happen silently.

-- 4.2 Revert the unique index to its original 2-column form.
ALTER TABLE cre_design_tool_knowledge_rules DROP INDEX `uq_design_tool_knowledge_rules_scope`;
ALTER TABLE cre_design_tool_knowledge_rules ADD UNIQUE KEY `uq_design_tool_knowledge_rules_scope` (`tool_id`,`knowledge_scope`);

-- 4.3 Revert field_code column (drop it entirely).
ALTER TABLE cre_design_tool_knowledge_rules DROP COLUMN `field_code`;

-- 4.4 Revert the knowledge_scope CHECK constraint to its original 3-value form.
--     Will fail if any row has knowledge_scope = 'design_job' - see 4.1's second query above.
ALTER TABLE cre_design_tool_knowledge_rules DROP CONSTRAINT `chk_design_tool_knowledge_rules_scope`;
ALTER TABLE cre_design_tool_knowledge_rules
  ADD CONSTRAINT `chk_design_tool_knowledge_rules_scope`
  CHECK ((`knowledge_scope` in (_utf8mb4'project',_utf8mb4'property',_utf8mb4'image')));

-- 4.5 Revert the 18 additive columns (irreversible - see header note).
ALTER TABLE cre_projects
  DROP COLUMN `goals`, DROP COLUMN `hoa_rules`, DROP COLUMN `climate`,
  DROP COLUMN `budget_low`, DROP COLUMN `budget_high`,
  DROP COLUMN `preferred_styles`, DROP COLUMN `design_preferences`;

ALTER TABLE cre_properties
  DROP COLUMN `bedrooms`, DROP COLUMN `bathrooms`, DROP COLUMN `construction_type`,
  DROP COLUMN `existing_materials`, DROP COLUMN `existing_colors`;

ALTER TABLE cre_property_images
  DROP COLUMN `camera_direction`, DROP COLUMN `existing_furniture`, DROP COLUMN `existing_lighting`;

ALTER TABLE cre_design_jobs
  DROP COLUMN `job_prompt`, DROP COLUMN `job_constraints`;

-- =============================================================================
-- END OF FILE
-- =============================================================================

-- =============================================================================
-- END OF FILE - phase_1_2a_knowledge_context_extension_rollback.sql
-- =============================================================================

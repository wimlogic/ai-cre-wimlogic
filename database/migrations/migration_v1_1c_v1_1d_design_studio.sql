-- ============================================================
-- AI-CRE WIMLOGIC
-- MIGRATION: V1.1C (Design Studio Tool Box) + V1.1D (Design Studio Core Workspace)
-- Scope: New cre_design_* domain tables + additive ALTER to cre_property_images
-- Target: MySQL 8.0.46, database `ai_cre_wimlogic`
-- Status: APPROVED FOR EXECUTION (post-review corrections applied)
--
-- Does NOT modify any existing table structure except the single approved
-- additive ALTER to `cre_property_images` (Section 11 of this file).
-- Does NOT create any V1.1G (Property Improvement / Contractor) table.
-- Does NOT alter `cre_workflow_executions.project_id` (verified from source,
-- no change required).
--
-- This is a forward-only migration file, not a schema rebuild script.
-- It intentionally contains NO `DROP TABLE IF EXISTS` statements: re-running
-- this file against an already-initialized Design Studio schema must never
-- silently delete business data. If a table already exists, this migration
-- will fail loudly with an "already exists" error rather than dropping and
-- recreating it - that failure is the correct, safe behavior.
--
-- Foreign key enforcement (FOREIGN_KEY_CHECKS) is left ENABLED throughout.
-- All ten tables below are ordered so that every FK target already exists
-- at the point of creation, so disabling FK checks is unnecessary.
--
-- Migration order (FK-safe):
--   1. cre_design_tools
--   2. cre_design_tool_options
--   3. cre_design_tool_image_requirements
--   4. cre_design_tool_knowledge_rules
--   5. cre_design_jobs
--   6. cre_design_job_executions
--   7. cre_design_job_images
--   8. cre_design_image_versions
--   9. cre_design_image_lineage
--  10. cre_approved_design_baselines
--  11. ALTER cre_property_images (additive, independent of order above)
-- ============================================================

SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';

-- ============================================================
-- 1. cre_design_tools
-- Tool catalog. Business-facing action (e.g. Exterior Remodel).
-- Note: no min_image_count / max_image_count here by design -
-- cre_design_tool_image_requirements is the single source of truth
-- for image-count validation (avoids two sources of truth).
-- ============================================================

CREATE TABLE `cre_design_tools` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tool_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `tool_name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `design_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `workflow_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `card_image_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `icon_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `business_description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `business_purpose` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `business_instructions` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `input_config_json` json DEFAULT NULL,
  `output_expectations_json` json DEFAULT NULL,
  `status` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'active',
  `display_order` int NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_design_tools_tool_code` (`tool_code`),
  KEY `idx_design_tools_status` (`status`),
  KEY `idx_design_tools_design_type` (`design_type`),
  KEY `idx_design_tools_display_order` (`display_order`),
  CONSTRAINT `chk_design_tools_status` CHECK (`status` in ('active','inactive','archived'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- 2. cre_design_tool_options
-- Per-Tool configurable option definitions (Design Style, Creativity, etc).
-- ============================================================

CREATE TABLE `cre_design_tool_options` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tool_id` bigint NOT NULL,
  `option_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `option_label` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `option_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `allowed_values_json` json DEFAULT NULL,
  `default_value` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `is_required` tinyint(1) NOT NULL DEFAULT '0',
  `display_order` int NOT NULL DEFAULT '0',
  `status` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'active',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_design_tool_options_tool_option` (`tool_id`,`option_code`),
  KEY `idx_design_tool_options_tool_id` (`tool_id`),
  CONSTRAINT `chk_design_tool_options_type` CHECK (`option_type` in ('select','multiselect','boolean','number','text','slider')),
  CONSTRAINT `fk_design_tool_options_tool` FOREIGN KEY (`tool_id`) REFERENCES `cre_design_tools` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- 3. cre_design_tool_image_requirements
-- Single source of truth for per-Tool image-count/role validation.
-- ============================================================

CREATE TABLE `cre_design_tool_image_requirements` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tool_id` bigint NOT NULL,
  `input_role` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `allowed_image_roles_json` json DEFAULT NULL,
  `min_count` int NOT NULL DEFAULT '0',
  `max_count` int DEFAULT NULL,
  `display_order` int NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_design_tool_img_req_tool_role` (`tool_id`,`input_role`),
  KEY `idx_design_tool_img_req_tool_id` (`tool_id`),
  CONSTRAINT `chk_design_tool_img_req_role` CHECK (`input_role` in ('primary','supporting','reference')),
  CONSTRAINT `fk_design_tool_img_req_tool` FOREIGN KEY (`tool_id`) REFERENCES `cre_design_tools` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- 4. cre_design_tool_knowledge_rules
-- Simplified V1.1C/D structure. No usage_mode / generic rule_json -
-- Project Knowledge and Property Knowledge are not yet first-class
-- entities, so a generic rule engine has no structured target.
-- ============================================================

CREATE TABLE `cre_design_tool_knowledge_rules` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tool_id` bigint NOT NULL,
  `knowledge_scope` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_required` tinyint(1) NOT NULL DEFAULT '0',
  `include_in_context` tinyint(1) NOT NULL DEFAULT '1',
  `instructions` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_design_tool_knowledge_rules_scope` (`tool_id`,`knowledge_scope`),
  KEY `idx_design_tool_knowledge_rules_tool_id` (`tool_id`),
  CONSTRAINT `chk_design_tool_knowledge_rules_scope` CHECK (`knowledge_scope` in ('project','property','image')),
  CONSTRAINT `fk_design_tool_knowledge_rules_tool` FOREIGN KEY (`tool_id`) REFERENCES `cre_design_tools` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- 5. cre_design_jobs
-- Persistent business job (NOT the same as a Workflow Execution attempt).
-- workflow_execution_id is intentionally NOT a column here - see
-- cre_design_job_executions (table 6) for the 1-job-to-many-attempts
-- association that preserves retry history.
--
-- Three distinct JSON snapshots are kept deliberately separate:
--   tool_options_json      = frozen user-selected Tool configuration
--   effective_context_json = frozen assembled Project + Property +
--                             selected Image Knowledge context
--   submitted_payload_json = the exact frozen AI-CRE Business Job payload
--                             actually submitted for workflow processing
--                             (auditable, used for retry comparison, and
--                             consumed by the future V1.1G handoff)
-- ============================================================

CREATE TABLE `cre_design_jobs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `job_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `project_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `property_id` bigint NOT NULL,
  `tool_id` bigint NOT NULL,
  `tool_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `design_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `workflow_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `tool_options_json` json DEFAULT NULL,
  `effective_context_json` json DEFAULT NULL,
  `submitted_payload_json` json DEFAULT NULL,
  `status` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'draft',
  `requested_by` bigint DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_design_jobs_job_number` (`job_number`),
  KEY `idx_design_jobs_property_id` (`property_id`),
  KEY `idx_design_jobs_project_id` (`project_id`),
  KEY `idx_design_jobs_tool_id` (`tool_id`),
  KEY `idx_design_jobs_status` (`status`),
  CONSTRAINT `chk_design_jobs_status` CHECK (`status` in ('draft','submitted','processing','completed','failed','cancelled')),
  CONSTRAINT `fk_design_jobs_property` FOREIGN KEY (`property_id`) REFERENCES `cre_properties` (`id`),
  CONSTRAINT `fk_design_jobs_tool` FOREIGN KEY (`tool_id`) REFERENCES `cre_design_tools` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- 6. cre_design_job_executions
-- Associates ONE Design Job with MANY Workflow Execution attempts.
-- Retry = new row here (new attempt_number) + new cre_workflow_executions
-- row via the existing, unmodified execution service. Nothing is deleted
-- or overwritten on retry.
-- ============================================================

CREATE TABLE `cre_design_job_executions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `design_job_id` bigint NOT NULL,
  `workflow_execution_id` bigint NOT NULL,
  `attempt_number` int NOT NULL,
  `is_current` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_design_job_executions_attempt` (`design_job_id`,`attempt_number`),
  UNIQUE KEY `uq_design_job_executions_execution` (`workflow_execution_id`),
  KEY `idx_design_job_executions_job_id` (`design_job_id`),
  CONSTRAINT `fk_design_job_executions_job` FOREIGN KEY (`design_job_id`) REFERENCES `cre_design_jobs` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_design_job_executions_execution` FOREIGN KEY (`workflow_execution_id`) REFERENCES `cre_workflow_executions` (`execution_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- 7. cre_design_job_images
-- Selected Property Images (M:N) that are inputs to a Design Job,
-- each with an input role and a frozen per-image knowledge snapshot.
-- ============================================================

CREATE TABLE `cre_design_job_images` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `design_job_id` bigint NOT NULL,
  `property_image_id` bigint NOT NULL,
  `input_role` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'primary',
  `image_knowledge_snapshot_json` json DEFAULT NULL,
  `display_order` int NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_design_job_images_job_image` (`design_job_id`,`property_image_id`),
  KEY `idx_design_job_images_property_image_id` (`property_image_id`),
  CONSTRAINT `chk_design_job_images_input_role` CHECK (`input_role` in ('primary','supporting','reference')),
  CONSTRAINT `fk_design_job_images_job` FOREIGN KEY (`design_job_id`) REFERENCES `cre_design_jobs` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_design_job_images_property_image` FOREIGN KEY (`property_image_id`) REFERENCES `cre_property_images` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- 8. cre_design_image_versions
-- Every generated result. Nothing is overwritten. workflow_execution_id
-- points directly at the specific attempt that produced this version
-- (distinct from the job-level attempt bookkeeping in table 6).
-- generated_asset_id is an OPTIONAL future promotion reference only -
-- approval never auto-populates it (see cre_approved_design_baselines).
--
-- This table intentionally has NO parent_version_id column. All ancestry -
-- including prior-version -> new-version refinement chains - is owned
-- exclusively by cre_design_image_lineage (table 9), so ancestry is never
-- tracked in two places at once.
-- ============================================================

CREATE TABLE `cre_design_image_versions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `version_uid` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `design_job_id` bigint NOT NULL,
  `property_id` bigint NOT NULL,
  `workflow_execution_id` bigint NOT NULL,
  `version_number` int NOT NULL,
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `storage_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `thumbnail_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `mime_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `file_size` bigint DEFAULT NULL,
  `width` int DEFAULT NULL,
  `height` int DEFAULT NULL,
  `generated_asset_id` bigint DEFAULT NULL,
  `status` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'generated',
  `generated_at` datetime NOT NULL,
  `generated_by` bigint DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_design_image_versions_uid` (`version_uid`),
  UNIQUE KEY `uq_design_image_versions_job_version` (`design_job_id`,`version_number`),
  KEY `idx_design_image_versions_property_id` (`property_id`),
  KEY `idx_design_image_versions_status` (`status`),
  KEY `idx_design_image_versions_workflow_execution_id` (`workflow_execution_id`),
  CONSTRAINT `chk_design_image_versions_status` CHECK (`status` in ('generated','rejected','approved','superseded')),
  CONSTRAINT `fk_design_image_versions_job` FOREIGN KEY (`design_job_id`) REFERENCES `cre_design_jobs` (`id`),
  CONSTRAINT `fk_design_image_versions_property` FOREIGN KEY (`property_id`) REFERENCES `cre_properties` (`id`),
  CONSTRAINT `fk_design_image_versions_execution` FOREIGN KEY (`workflow_execution_id`) REFERENCES `cre_workflow_executions` (`execution_id`),
  CONSTRAINT `fk_design_image_versions_asset` FOREIGN KEY (`generated_asset_id`) REFERENCES `cre_generated_assets` (`asset_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- 9. cre_design_image_lineage
-- The SOLE authoritative source for all generated-version ancestry.
-- Supports:
--   ONE Property Image  -> MANY generated versions
--   MANY source images  -> ONE generated version
--   Prior version       -> New version (refinement chains, via
--                          source_type = 'image_version')
--
-- cre_design_image_versions carries no parent_version_id of its own -
-- ancestry, including version-to-version refinement chains, is never
-- duplicated across the two tables.
--
-- CHECK constraint enforces exactly-one-source-populated (XOR) at the
-- database level (MySQL 8.0.16+ enforces CHECK; 8.0.46 qualifies).
--
-- Dedup is enforced via TWO separate composite unique keys, one per
-- nullable source column, rather than one combined key across both -
-- MySQL treats NULL as distinct from NULL in unique keys, so a single
-- 4-column composite key would NOT prevent duplicate rows. Splitting
-- into two keys, each covering one column that is always non-NULL for
-- its relevant source_type, gives a real duplicate guarantee.
-- ============================================================

CREATE TABLE `cre_design_image_lineage` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `image_version_id` bigint NOT NULL,
  `source_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `source_property_image_id` bigint DEFAULT NULL,
  `source_image_version_id` bigint DEFAULT NULL,
  `lineage_role` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'primary',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_design_image_lineage_version_property_image` (`image_version_id`,`source_property_image_id`),
  UNIQUE KEY `uq_design_image_lineage_version_source_version` (`image_version_id`,`source_image_version_id`),
  KEY `idx_design_image_lineage_source_property_image_id` (`source_property_image_id`),
  KEY `idx_design_image_lineage_source_image_version_id` (`source_image_version_id`),
  CONSTRAINT `chk_design_image_lineage_source_type` CHECK (`source_type` in ('property_image','image_version')),
  CONSTRAINT `chk_design_image_lineage_source_xor` CHECK (
    (`source_type` = 'property_image' AND `source_property_image_id` IS NOT NULL AND `source_image_version_id` IS NULL)
    OR
    (`source_type` = 'image_version' AND `source_image_version_id` IS NOT NULL AND `source_property_image_id` IS NULL)
  ),
  CONSTRAINT `chk_design_image_lineage_role` CHECK (`lineage_role` in ('primary','supporting','reference','parent')),
  CONSTRAINT `fk_design_image_lineage_version` FOREIGN KEY (`image_version_id`) REFERENCES `cre_design_image_versions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_design_image_lineage_source_property_image` FOREIGN KEY (`source_property_image_id`) REFERENCES `cre_property_images` (`id`),
  CONSTRAINT `fk_design_image_lineage_source_version` FOREIGN KEY (`source_image_version_id`) REFERENCES `cre_design_image_versions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- 10. cre_approved_design_baselines
-- Formal V1.1D -> V1.1G business handoff. Self-sufficient snapshot -
-- never requires reconstructing historical mutable state.
--
-- Supersede rule is BOTH database-constrained and service-enforced:
--   - active_scope_key collapses to NULL for every non-active row
--     (MySQL never treats NULL as equal to NULL under a unique index),
--     so UNIQUE(active_scope_key) makes it structurally impossible for
--     two ACTIVE baselines to exist for the same
--     property_id + design_type + design_scope - while placing no limit
--     on how many superseded rows accumulate. Nothing is ever deleted.
--   - The SERVICE still owns sequencing: it must flip the prior active
--     row to 'superseded' before activating a new one; the DB constraint
--     is what makes that transaction safe, not a replacement for it.
--
-- Approval does NOT automatically promote into cre_generated_assets.
-- ============================================================

CREATE TABLE `cre_approved_design_baselines` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `baseline_uid` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `project_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `property_id` bigint NOT NULL,
  `design_job_id` bigint NOT NULL,
  `image_version_id` bigint NOT NULL,
  `tool_id` bigint NOT NULL,
  `tool_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `design_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `design_scope` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `tool_options_json` json DEFAULT NULL,
  `effective_context_json` json DEFAULT NULL,
  `status` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'active',
  `active_scope_key` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci
    GENERATED ALWAYS AS (
      CASE WHEN `status` = 'active'
        THEN CONCAT(`property_id`, '|', `design_type`, '|', `design_scope`)
        ELSE NULL
      END
    ) STORED,
  `approved_by` bigint DEFAULT NULL,
  `approved_at` datetime NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_approved_design_baselines_uid` (`baseline_uid`),
  UNIQUE KEY `uq_approved_design_baselines_image_version` (`image_version_id`),
  UNIQUE KEY `uq_approved_design_baselines_active_scope` (`active_scope_key`),
  KEY `idx_approved_design_baselines_property_id` (`property_id`),
  KEY `idx_approved_design_baselines_project_id` (`project_id`),
  KEY `idx_approved_design_baselines_status` (`status`),
  KEY `idx_approved_design_baselines_type_scope` (`design_type`,`design_scope`),
  CONSTRAINT `chk_approved_design_baselines_status` CHECK (`status` in ('active','superseded')),
  CONSTRAINT `fk_approved_design_baselines_property` FOREIGN KEY (`property_id`) REFERENCES `cre_properties` (`id`),
  CONSTRAINT `fk_approved_design_baselines_job` FOREIGN KEY (`design_job_id`) REFERENCES `cre_design_jobs` (`id`),
  CONSTRAINT `fk_approved_design_baselines_version` FOREIGN KEY (`image_version_id`) REFERENCES `cre_design_image_versions` (`id`),
  CONSTRAINT `fk_approved_design_baselines_tool` FOREIGN KEY (`tool_id`) REFERENCES `cre_design_tools` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- 11. ALTER cre_property_images (additive only)
-- Closes the verified Image AI Knowledge gap against the locked
-- 06_AI_KNOWLEDGE_STANDARD (ai_prompt, tags, constraints, priority)
-- and adds the missing primary-image indicator (is_primary).
--
-- INDEX (property_id, is_primary) is a PLAIN, NON-UNIQUE index added
-- only for lookup performance. It deliberately does NOT enforce
-- "exactly one primary image per property" as a database constraint,
-- per instruction - a UNIQUE constraint on this pair would incorrectly
-- cap a property at one non-primary image, since is_primary = 0 rows
-- are not NULL and would collide under a unique index. The
-- one-primary-per-property rule remains SERVICE-ENFORCED: the service
-- must clear is_primary on a property's other images, in the same
-- transaction, before setting a new primary.
-- ============================================================

ALTER TABLE `cre_property_images`
  ADD COLUMN `ai_prompt` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL AFTER `notes`,
  ADD COLUMN `tags` json NULL AFTER `ai_prompt`,
  ADD COLUMN `constraints` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL AFTER `tags`,
  ADD COLUMN `priority` int NULL AFTER `constraints`,
  ADD COLUMN `is_primary` tinyint(1) NOT NULL DEFAULT '0' AFTER `priority`,
  ADD INDEX `idx_property_images_primary` (`property_id`, `is_primary`);


-- ============================================================
-- END OF MIGRATION
-- ============================================================

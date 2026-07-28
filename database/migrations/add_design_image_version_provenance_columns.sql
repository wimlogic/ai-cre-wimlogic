-- =============================================================================
-- add_design_image_version_provenance_columns.sql
--
-- AIHOME Image Result Integration - IMAGE_DESIGN workflow support.
--
-- Adds SIX nullable columns to cre_design_image_versions, preserving
-- provenance for images AIHOME downloads from a DEV-TOOLS IMAGE_DESIGN
-- result and imports into its own permanent storage:
--
--   source_image_id     - DEV-TOOLS' own artifact identifier (design_images[].image_id)
--   source_provider     - the AI provider that generated the image (e.g. "OpenAI")
--   source_model        - the specific model used (e.g. "gpt-image-2")
--   source_checksum     - the checksum DEV-TOOLS reported for the artifact,
--                         preserved for audit even after AIHOME independently
--                         verifies the downloaded bytes against it
--   source_artifact_url - the DEV-TOOLS artifact URL the image was downloaded
--                         from (temporary Runtime provenance, per
--                         AIHOME_IMAGE_DESIGN_OUTPUT_SPEC.md's "AIHOME Import
--                         Responsibilities" - preserved as a record of where
--                         it came from, never used for AIHOME's own display)
--   quality_approved    - DEV-TOOLS' own quality_review.approved outcome at
--                         import time, so AIHOME's UI can surface a warning
--                         for an unapproved image without needing to store
--                         the full quality_review.issues/recommendations text
--
-- All four are NULL for every DesignImageVersion created through any
-- OTHER existing path (Design Studio's own generation flow already
-- populates width/height/mime_type/file_size directly; this migration
-- adds nothing there) - this is additive, provenance-only, and does not
-- change the meaning of any existing column.
-- =============================================================================


-- SECTION 1 - PRE-MIGRATION VERIFICATION

SELECT VERSION();

SELECT COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'cre_design_image_versions'
  AND COLUMN_NAME IN ('source_image_id', 'source_provider', 'source_model', 'source_checksum', 'source_artifact_url', 'quality_approved');
-- Expect ZERO rows.

SELECT COUNT(*) AS row_count_before FROM cre_design_image_versions;


-- SECTION 2 - MIGRATION

SET @col_exists = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_design_image_versions'
    AND COLUMN_NAME = 'source_image_id'
);
SET @sql = IF(@col_exists = 0,
  'ALTER TABLE cre_design_image_versions
     ADD COLUMN `source_image_id` VARCHAR(120) NULL AFTER `height`,
     ADD COLUMN `source_provider` VARCHAR(80) NULL AFTER `source_image_id`,
     ADD COLUMN `source_model` VARCHAR(120) NULL AFTER `source_provider`,
     ADD COLUMN `source_checksum` VARCHAR(128) NULL AFTER `source_model`,
     ADD COLUMN `source_artifact_url` VARCHAR(500) NULL AFTER `source_checksum`,
     ADD COLUMN `quality_approved` TINYINT(1) NULL AFTER `source_artifact_url`',
  'SELECT ''source_image_id and related columns already exist, skipped'''
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- SECTION 3 - POST-MIGRATION VERIFICATION

SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'cre_design_image_versions'
  AND COLUMN_NAME IN ('source_image_id', 'source_provider', 'source_model', 'source_checksum', 'source_artifact_url', 'quality_approved');
-- Expect exactly 6 rows, all IS_NULLABLE = 'YES'.

SELECT COUNT(*) AS row_count_after FROM cre_design_image_versions;
-- Must be unchanged from Section 1.


-- SECTION 4 - ROLLBACK (only if genuinely needed)

-- ALTER TABLE cre_design_image_versions
--   DROP COLUMN `source_image_id`,
--   DROP COLUMN `source_provider`,
--   DROP COLUMN `source_model`,
--   DROP COLUMN `source_checksum`,
--   DROP COLUMN `source_artifact_url`,
--   DROP COLUMN `quality_approved`;

-- =============================================================================
-- END OF FILE
-- =============================================================================

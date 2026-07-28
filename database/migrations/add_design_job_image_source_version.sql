-- =============================================================================
-- add_design_job_image_source_version.sql
--
-- AIHOME Design Studio V2 - Image Workspace Evolution.
--
-- Approved design: extends cre_design_job_images to accept EITHER an
-- original Property Image OR a prior DesignImageVersion as a Design Job's
-- reference image - exactly the same two-source-type shape already used
-- by cre_design_image_lineage (source_type: "property_image" /
-- "image_version"), applied here where it was missing.
--
-- property_image_id becomes NULLABLE: each row references exactly one of
-- the two sources, never both, never neither - enforced at the
-- application layer (design_job_service.set_images()), matching how
-- lineage's own two-source-type rows are validated in the same file
-- rather than via a DB CHECK constraint (consistent with this project's
-- existing validation-lives-in-the-service-layer convention).
-- =============================================================================


-- SECTION 1 - PRE-MIGRATION VERIFICATION

SELECT VERSION();

SELECT COLUMN_NAME, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'cre_design_job_images'
  AND COLUMN_NAME IN ('property_image_id', 'source_image_version_id');
-- Expect ONE row (property_image_id, IS_NULLABLE = 'NO') before migration.

SELECT COUNT(*) AS row_count_before FROM cre_design_job_images;


-- SECTION 2 - MIGRATION

SET @col_exists = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cre_design_job_images'
    AND COLUMN_NAME = 'source_image_version_id'
);
SET @sql = IF(@col_exists = 0,
  'ALTER TABLE cre_design_job_images
     MODIFY COLUMN `property_image_id` BIGINT NULL,
     ADD COLUMN `source_image_version_id` BIGINT NULL AFTER `property_image_id`,
     ADD CONSTRAINT `fk_design_job_images_source_version`
       FOREIGN KEY (`source_image_version_id`)
       REFERENCES `cre_design_image_versions` (`id`)',
  'SELECT ''source_image_version_id already exists, skipped'''
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- SECTION 3 - POST-MIGRATION VERIFICATION

SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'cre_design_job_images'
  AND COLUMN_NAME IN ('property_image_id', 'source_image_version_id');
-- Expect 2 rows: property_image_id now IS_NULLABLE = 'YES',
-- source_image_version_id present, IS_NULLABLE = 'YES'.

SELECT COUNT(*) AS row_count_after FROM cre_design_job_images;
-- Must be unchanged from Section 1. Every pre-existing row keeps its
-- original property_image_id value untouched - this migration only
-- widens what's ALLOWED, it does not touch existing data.


-- SECTION 4 - ROLLBACK (only if genuinely needed; note this only safely
-- rolls back if no row has yet used source_image_version_id)

-- ALTER TABLE cre_design_job_images
--   DROP FOREIGN KEY fk_design_job_images_source_version,
--   DROP COLUMN source_image_version_id,
--   MODIFY COLUMN property_image_id BIGINT NOT NULL;

-- =============================================================================
-- END OF FILE
-- =============================================================================

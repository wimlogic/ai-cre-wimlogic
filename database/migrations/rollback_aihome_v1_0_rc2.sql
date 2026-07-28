-- AIHOME v1.0 RC2 rollback.
-- Run only after stopping workflow submissions and taking a database backup.
-- The source-version rollback aborts if RC2 data depends on the new column.

DELIMITER //
CREATE PROCEDURE rollback_rc2_source_versions()
BEGIN
  IF EXISTS (
    SELECT 1 FROM cre_design_job_images
    WHERE source_image_version_id IS NOT NULL
  ) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'RC2 rollback blocked: design jobs reference source image versions';
  ELSE
    ALTER TABLE cre_design_job_images
      DROP FOREIGN KEY fk_design_job_images_source_version,
      DROP COLUMN source_image_version_id,
      MODIFY COLUMN property_image_id BIGINT NOT NULL;
  END IF;
END//
DELIMITER ;
CALL rollback_rc2_source_versions();
DROP PROCEDURE rollback_rc2_source_versions;

DELETE o FROM cre_design_tool_options o
JOIN cre_design_tools t ON t.id = o.tool_id
WHERE t.tool_code IN (
  'STYLE_SPANISH_MEDITERRANEAN', 'STYLE_EUROPEAN_CLASSIC',
  'STYLE_ITALIAN_STUCCO', 'STYLE_JAPANESE_BAMBOO'
);
DELETE r FROM cre_design_tool_image_requirements r
JOIN cre_design_tools t ON t.id = r.tool_id
WHERE t.tool_code IN (
  'STYLE_SPANISH_MEDITERRANEAN', 'STYLE_EUROPEAN_CLASSIC',
  'STYLE_ITALIAN_STUCCO', 'STYLE_JAPANESE_BAMBOO'
);
DELETE FROM cre_design_tools
WHERE tool_code IN (
  'STYLE_SPANISH_MEDITERRANEAN', 'STYLE_EUROPEAN_CLASSIC',
  'STYLE_ITALIAN_STUCCO', 'STYLE_JAPANESE_BAMBOO'
);

ALTER TABLE cre_design_image_versions
  DROP COLUMN source_image_id,
  DROP COLUMN source_provider,
  DROP COLUMN source_model,
  DROP COLUMN source_checksum,
  DROP COLUMN source_artifact_url,
  DROP COLUMN quality_approved;

ALTER TABLE cre_workflow_executions
  DROP COLUMN additional_business_intents,
  DROP COLUMN result_sync_error;

ALTER TABLE cre_approved_design_baselines
  DROP INDEX uq_approved_design_baselines_active_scope;

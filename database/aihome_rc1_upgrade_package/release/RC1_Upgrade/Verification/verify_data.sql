-- =============================================================================
-- verify_data.sql — AIHOME Community Edition v1.0 RC1
-- Data-integrity verification for an upgraded (existing) AIHOME database.
--
-- Every check is a hard invariant of the RC1 business logic. Each states its
-- EXPECTED result inline. All checks are read-only.
-- =============================================================================

-- CHECK D1: no duplicate ACTIVE baseline for any
-- (property_id, design_type, design_scope) scope. This is the invariant the
-- active_scope_key UNIQUE constraint enforces structurally; this query
-- verifies it also holds at the data level.
-- EXPECTED: zero rows
SELECT property_id, design_type, design_scope, COUNT(*) AS active_count
FROM cre_approved_design_baselines
WHERE status = 'active'
GROUP BY property_id, design_type, design_scope
HAVING COUNT(*) > 1;

-- CHECK D2: no duplicate (design_job_id, version_number) pairs.
-- EXPECTED: zero rows
SELECT design_job_id, version_number, COUNT(*) AS dup_count
FROM cre_design_image_versions
GROUP BY design_job_id, version_number
HAVING COUNT(*) > 1;

-- CHECK D3: lineage source-type consistency — every lineage row of
-- source_type 'property_image' must carry source_property_image_id, and
-- every 'image_version' row must carry source_image_version_id.
-- EXPECTED: violation_count = 0
SELECT COUNT(*) AS violation_count
FROM cre_design_image_lineage
WHERE (source_type = 'property_image' AND source_property_image_id IS NULL)
   OR (source_type = 'image_version'  AND source_image_version_id  IS NULL);

-- CHECK D4: no orphaned baselines — every baseline's image_version_id
-- resolves to a real version row. (FK-guaranteed on a healthy schema; this
-- confirms it at the data level regardless.)
-- EXPECTED: orphan_count = 0
SELECT COUNT(*) AS orphan_count
FROM cre_approved_design_baselines b
LEFT JOIN cre_design_image_versions v ON v.id = b.image_version_id
WHERE v.id IS NULL;

-- CHECK D5: no version is referenced as its own lineage source
-- (a version cannot be its own parent).
-- EXPECTED: self_reference_count = 0
SELECT COUNT(*) AS self_reference_count
FROM cre_design_image_lineage
WHERE source_type = 'image_version'
  AND source_image_version_id = image_version_id;

-- CHECK D6: baseline status domain — every row is 'active' or 'superseded'.
-- (Also CHECK-constrained in this schema; verified at data level regardless.)
-- EXPECTED: invalid_status_count = 0
SELECT COUNT(*) AS invalid_status_count
FROM cre_approved_design_baselines
WHERE status NOT IN ('active', 'superseded');

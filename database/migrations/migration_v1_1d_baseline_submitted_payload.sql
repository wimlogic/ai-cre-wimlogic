-- ============================================================
-- AI-CRE WIMLOGIC
-- MIGRATION: V1.1D corrective fix - Approved Design Baseline
-- Scope: Single additive column on cre_approved_design_baselines
-- Target: MySQL 8.0.46, database `ai_cre_wimlogic`
-- Status: APPROVED FOR EXECUTION
--
-- Background: the original V1.1C/D migration correctly added
-- submitted_payload_json to cre_design_jobs, but the same column was
-- missed on cre_approved_design_baselines. Verified directly against
-- the post-migration ai_cre_schema.sql: cre_design_jobs carries the
-- column; cre_approved_design_baselines does not. This migration closes
-- that gap only - nothing else on the table is touched.
--
-- Purpose of the column: the baseline row snapshots
--   tool_options_json      = frozen Tool configuration at approval
--   effective_context_json = frozen assembled Knowledge context at approval
-- but was still missing
--   submitted_payload_json = the exact frozen AI-CRE Business Job payload
--                            that was actually submitted for workflow
--                            processing - required so the Approved Design
--                            Baseline remains fully self-sufficient for
--                            V1.1G consumption without needing to
--                            reconstruct historical mutable state from
--                            cre_design_jobs.
--
-- This is a single additive column. No existing data is affected, no
-- other column changes, no FK or index changes. No DROP TABLE statements.
-- Foreign key enforcement is left enabled (untouched) throughout.
-- ============================================================

ALTER TABLE `cre_approved_design_baselines`
  ADD COLUMN `submitted_payload_json` json DEFAULT NULL AFTER `effective_context_json`;

-- ============================================================
-- END OF MIGRATION
-- ============================================================

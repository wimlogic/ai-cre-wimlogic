# Deploy_RC1.md — AIHOME Community Edition v1.0 RC1 Upgrade

**Package type:** Upgrade of an EXISTING AIHOME installation. Not a fresh-install package.
**Determinism guarantee:** Follow this document top to bottom. There are no decisions to make about which migration scripts to run.

---

## 1. Version

| | |
|---|---|
| **Current version** | AIHOME development database, evolved through Phase 1.2A and subsequent hotfixes (authoritative state: the audited `ai_cre_wimlogic_schema.sql`, 28 tables) |
| **Target version** | AIHOME Community Edition v1.0 RC1 |
| **Code delta** | Phases A–E (storage, services, WACP business intents, API, frontend, model fix) |
| **Schema delta** | **NONE — see §2** |

## 2. Required SQL Scripts, In Exact Execution Order

**NONE. Zero migrations are required.**

This is the audited result, not an assumption. A full programmatic diff was executed between (a) the authoritative uploaded schema loaded into a real MySQL 8.0.46 instance and (b) the schema produced by the current RC1 SQLAlchemy models, comparing tables, columns, types, nullability, unique constraints (by semantic column-set, not name), foreign keys (by semantic column→reference, not name), generated columns, and triggers. The result:

- **Tables:** 0 missing. All three Phase 1 tables (`cre_design_image_versions`, `cre_design_image_lineage`, `cre_approved_design_baselines`) already exist.
- **Columns:** 0 missing. Both post-1.2A hotfix columns are already present: `cre_workflow_executions.result_sync_error` and the `active_scope_key` generated column.
- **Unique constraints:** 0 missing. Critically, `uq_approved_design_baselines_active_scope` — the only schema change produced by Phases A–E — **already exists in this database.** The Phase E defect was in the ORM model declaration only; this database was provisioned from the maintained SQL reference, which always had the constraint. The model fix ships in the code; the database needs nothing.
- **Generated columns:** exactly 1 (`active_scope_key`), no duplicates. **Triggers:** 0.

**RC1 is therefore a code-only upgrade for this database.**

## 3. Scripts That Must NOT Be Executed (Historical)

These exist in the repository / prior consolidated package. Every one is already reflected in the current database. Do not run them:

| Script | Why not |
|---|---|
| `001_add_approved_baseline_active_scope_unique_constraint.sql` | Constraint already present (verified: `NON_UNIQUE=0` on `active_scope_key`). Idempotent, so accidentally running it is harmless — but it is not part of this upgrade |
| `add_result_sync_error_column.sql` | Column already present (verified: `text`, nullable) |
| `migration_v1_1c_v1_1d_design_studio.sql` | All Design Studio tables already present |
| `migration_v1_1d_baseline_submitted_payload.sql` | `submitted_payload_json` already present |
| `phase_1_2a_knowledge_context_extension.sql` (+ its rollback) | This IS a Phase 1.2A database; all 1.2A columns verified present (column diff: zero missing) |
| `ai_cre_schema_updated_reference.sql` / any full reference schema | Fresh installs only. Never run a full schema file against an existing database |

## 4. Upgrade Procedure

1. Take a database backup (standard practice; no schema or data will be modified, but take one anyway).
2. Run `Verification/verify_schema.sql` — confirm results match §5 **before** deploying code. If any check deviates, STOP: the database is not in the audited state this package was built for.
3. Run `Verification/verify_data.sql` — confirm results match §5.
4. Deploy the RC1 code (backend + frontend overlay from the RC1 code package), rebuild frontend, restart backend.
5. Re-run both verification scripts. Results must be identical to step 2–3 (the deployment changes no schema and no data).
6. Perform the smoke tests from the RC1 deployment guide (open an image detail modal; confirm Versions/Compare/Approval sections render; confirm the empty state on an image with no versions).

## 5. Expected Verification Results

These are the exact outputs obtained when both scripts were executed against the authoritative schema on MySQL 8.0.46. Any deviation means the database is not in the expected state.

**verify_schema.sql:**

| Check | Expected |
|---|---|
| 1 — RC1 tables | `table_count = 3` |
| 2 — generated column | 1 row: `active_scope_key`, EXTRA = `STORED GENERATED` |
| 3 — active-scope unique | 1 row: `uq_approved_design_baselines_active_scope`, `NON_UNIQUE = 0` |
| 4 — result_sync_error | 1 row: `text`, `IS_NULLABLE = YES` |
| 5 — version uniqueness | 1 row: `uq_design_image_versions_job_version`, cols = `design_job_id,version_number` |
| 6 — lineage FKs | `fk_count = 3` |
| 7 — duplicate indexes | **zero rows** |
| 8 — generated columns inventory | exactly 1 row: `cre_approved_design_baselines` / `active_scope_key` |
| 9 — triggers | `trigger_count = 0` |

**verify_data.sql:**

| Check | Expected |
|---|---|
| D1 — duplicate active baselines | **zero rows** |
| D2 — duplicate version numbers | **zero rows** |
| D3 — lineage source-type consistency | `violation_count = 0` |
| D4 — orphaned baselines | `orphan_count = 0` |
| D5 — self-referencing lineage | `self_reference_count = 0` |
| D6 — baseline status domain | `invalid_status_count = 0` |

## 6. Rollback Order

**Database:** nothing to roll back — no migration is executed by this upgrade. The `Rollback/` folder documents this explicitly rather than containing placeholder scripts.

**Code:** revert the code overlay (restore prior backend/frontend files), rebuild frontend, restart backend. The database remains valid for both the prior code and RC1 code at all times during this upgrade — that is a direct consequence of the zero-schema-delta finding.

## 7. Documented Pre-Existing Drift (OUT OF SCOPE — do not "fix" during this upgrade)

The audit surfaced two categories of long-standing drift between the ORM models and the actual database. **Neither was caused by any Phase A–E change, neither affects RC1 behavior, and neither is part of this upgrade.** They are documented so they are known, not so they are acted on now:

1. **17 foreign keys declared by ORM models but absent on legacy tables** (`cre_concept_designs`, `cre_estimates`, `cre_generated_assets`, `cre_project_properties`, `cre_property_analysis_reports`, `cre_renovation_scenarios`, `cre_scan_jobs`, `cre_workflow_executions.property_id`). The Phase 1 tables have complete FKs; only pre-Phase-1 tables lack them. Adding them now would be out of scope, and could fail against legacy orphaned rows without a prior data audit. If desired, address as a separate housekeeping initiative with its own data-quality audit.
2. **Type-representation differences** (`tinyint` vs `int` for boolean-like flags, `timestamp` vs `datetime`, `enum` vs `varchar`, `longtext` vs `text`, nullable `created_at`/`updated_at` on some legacy tables). These are long-standing representational conventions between the hand-written reference schema and SQLAlchemy's generated DDL. Runtime-compatible in every case; no migration warranted.

Full details: `Release_Engineering_Summary.md`.

# Release Engineering Summary — AIHOME CE v1.0 RC1 Upgrade Package

## What Was Asked

Produce the minimum, deterministic database delta to upgrade an existing Phase 1.2A AIHOME database to RC1, treating the uploaded `ai_cre_wimlogic_schema.sql` as the authoritative current state — generating only migrations that are genuinely required, and explicitly stating if none are.

## How The Delta Was Determined (Method, Not Assertion)

1. The authoritative schema was loaded into a real MySQL 8.0.46 database (`db_actual`, 28 tables confirmed).
2. The current RC1 SQLAlchemy models were materialized into a second database (`db_models`) via `Base.metadata.create_all()`.
3. A programmatic diff compared both via `INFORMATION_SCHEMA`, on **semantic identity rather than names** (constraint/index names differ legitimately between the hand-written schema and generated DDL):
   - Tables (both directions)
   - Columns: existence, data type, nullability, generated-ness
   - Unique constraints: by (table, ordered column set)
   - Foreign keys: by (table, column, referenced table, referenced column)
   - Generated columns and triggers (duplicate detection)
4. Historical migration files were consulted **only** to confirm no change was being regenerated — per instruction, none were treated as evidence of what the database contains. The loaded schema itself was the sole source of truth.

## The Result: Zero Required Migrations

Every element the RC1 models require already exists in the authoritative database:

| RC1 requirement | State in authoritative DB | Model change that would have caused a migration |
|---|---|---|
| 3 Phase 1 tables (versions, lineage, baselines) | Present, complete, fully FK'd | None — Phase 1 activated pre-existing tables by design; no phase created tables |
| `result_sync_error` on `cre_workflow_executions` | Present (`text`, nullable) | Pre-Phase-1 hotfix; already applied to this DB |
| `active_scope_key` generated column | Present, `STORED GENERATED`, exactly one in schema | Pre-existing in reference schema |
| `uq_approved_design_baselines_active_scope` | **Present** (`NON_UNIQUE = 0`) | Phase E added this to the ORM model — the **only** schema-relevant change in all of A–E. But the defect was that the *model* lacked what the reference schema and this database *already had*. The fix ships in code; this database needs nothing |
| `UNIQUE(design_job_id, version_number)` | Present | None — pre-existing |
| Lineage FKs (3) | Present | None — pre-existing |

**Why each generated migration is necessary: no migration was generated, because none is necessary.** The previous consolidated package's migration `001` targeted databases bootstrapped via `create_all()` (which genuinely lacked the constraint — every test database did). This database is not one of them. Shipping that migration here anyway — "because it exists" — is precisely what this package was directed not to do. It is listed in Deploy_RC1.md §3 as historical, must-not-run.

## Validation Checklist (as required)

- ✓ No duplicate `ALTER TABLE` — trivially: zero ALTERs shipped
- ✓ No duplicate indexes — verified by query (zero same-column-set index pairs on RC1 tables); check permanently encoded as verify_schema.sql CHECK 7
- ✓ No duplicate constraints — unique-constraint diff by semantic column set: zero duplicates, zero missing
- ✓ No duplicate columns — column diff: zero missing, zero unexpected
- ✓ No duplicate foreign keys — FK diff by semantic reference: zero duplicates
- ✓ No duplicate triggers — zero triggers exist (CHECK 9)
- ✓ No duplicate generated columns — exactly one exists, as intended (CHECK 8)
- ✓ No unnecessary migrations — zero shipped; six historical scripts explicitly listed as must-not-run

## Findings Outside RC1 Scope (Documented, Deliberately Not Migrated)

The diff surfaced genuine, long-standing drift that predates Phase 1 entirely. Reporting it is part of an honest audit; migrating it is not part of this release:

**1. Seventeen FKs declared by ORM models, absent on legacy tables.** Affected: `cre_concept_designs` (4), `cre_property_analysis_reports` (5), `cre_project_properties` (2), `cre_renovation_scenarios` (2), `cre_estimates` (1), `cre_generated_assets` (1), `cre_scan_jobs` (1), `cre_workflow_executions.property_id` (1). Verified directly in the uploaded file: these legacy tables carry no FK constraints at all, while every Phase 1 table is fully constrained. No Phase A–E change declared, moved, or modified any of these relationships — this is inherited drift. Excluded because: (a) not caused by any RC1 model change, (b) RC1 behavior does not depend on DB-enforced integrity on those paths, and (c) adding FKs to legacy tables without a prior orphan-row data audit is a genuine production risk, the opposite of a minimum-change upgrade. Recommended as a separate, self-contained housekeeping initiative if wanted.

**2. Type-representation differences on legacy tables** (`tinyint` vs `int` flags, `timestamp` vs `datetime`, `enum` vs `varchar`, `longtext` vs `text`, nullable audit columns). Long-standing conventions of the hand-written schema vs SQLAlchemy DDL; runtime-compatible in every case; no migration warranted, and none generated.

## Determinism Statement

An operator following Deploy_RC1.md makes zero migration decisions: the required-scripts list is empty, the must-not-run list is explicit and complete, both verification scripts carry their exact expected outputs (obtained by real execution against the authoritative schema, with per-step success markers — an earlier verification run that silently produced empty output due to a dead database connection was detected and discarded rather than accepted as a pass), and rollback is a documented no-op on the database side.

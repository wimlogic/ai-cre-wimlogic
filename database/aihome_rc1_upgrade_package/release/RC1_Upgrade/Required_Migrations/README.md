# Required Migrations: NONE

This folder is intentionally empty of SQL files, and that emptiness is the
audited deliverable, not an omission.

A full programmatic schema diff (documented in Deploy_RC1.md §2 and
Release_Engineering_Summary.md) proved that the authoritative current
database already contains every schema element the RC1 SQLAlchemy models
require:

- All 3 Phase 1 tables — present
- All columns, including `result_sync_error` and `active_scope_key` — present
- The `uq_approved_design_baselines_active_scope` UNIQUE constraint — present
  (the only schema change Phases A–E produced; this database always had it,
  because it tracked the maintained SQL reference where the constraint was
  never missing — the Phase E defect existed only in the ORM declaration)

Per the release requirement — "If no migration is required, explicitly
state that. Do not include historical SQL simply because it exists in the
repository" — no migration files are shipped.

RC1 is a code-only upgrade for this database.

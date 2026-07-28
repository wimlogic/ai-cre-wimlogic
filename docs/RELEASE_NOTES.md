# AIHOME v1.0 RC2 Release Notes

Status: release candidate pending final validation and human approval.

## Highlights

- Multi-intent WACP submissions and WIM V2 result ingestion.
- Business-focused property intelligence reports.
- AI design image provenance, version history, inspection, and approval.
- Style-based design tools and expanded design-job workspace.

## Database

RC2 adds workflow intent/synchronization fields, image provenance fields,
source-version support, active-baseline uniqueness, and style-tool seed data.
Apply only the reviewed files in `database/migrations/` and retain a verified
pre-deployment backup.

## Compatibility

Existing single-intent WACP submissions remain supported. New database fields
are nullable and additive except for rollback of source-version support, which
requires confirmation that no RC2 source-version rows exist.

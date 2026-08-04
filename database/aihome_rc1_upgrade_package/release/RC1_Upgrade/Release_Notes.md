# Release Notes — AIHOME Community Edition v1.0 RC1 (Upgrade)

**Upgrade type:** Code-only. **Database migrations required: none** (audited — see `Release_Engineering_Summary.md`).

---

## For Operators

Your database already contains the complete RC1 schema. This upgrade deploys code and verifies; it changes no schema and no data. Total procedure: verify → deploy code → re-verify → smoke test (`Deploy_RC1.md`).

## What RC1 Delivers (code)

- **Property Intelligence** — structured analysis reports (Executive Summary, Key Findings, Business Health, Priority Actions, Recommendations, Conclusion) with per-property history. `PROPERTY_INTELLIGENCE` becomes the canonical business intent; `PROPERTY_ANALYSIS` remains a fully supported legacy alias.
- **Design Studio version workflow** — the Property Image detail view gains Versions / Compare / Approval as expandable sections: browse every generated design version with its lineage back to the original photo, compare any two side-by-side, and approve a version as the active baseline (supersede-based, idempotent, history preserved).
- **WACP routing** — Design Studio submits via `business_intent="DESIGN_STUDIO"`; AIHOME sends no workflow codes; workflow resolution remains entirely in the DEV-TOOLS WIM Module.
- **Model correctness fix** — the ORM model for approved baselines now declares the `active_scope_key` UNIQUE constraint **your database has always had**. The defect was model-side only; databases like this one, provisioned from the maintained SQL reference, were never exposed to it.

## Compatibility

- No breaking API changes; all new endpoints are additive under `/api/v1/design-studio/*`.
- No table, column, model, or endpoint renames.
- The database remains valid for both pre-RC1 and RC1 code throughout the upgrade — rollback is a code revert with no database step.

## Known Limitations (unchanged from the RC1 validation report)

1. `design_scope` is server-derived from the design job's primary image role (documented temporary Phase 1 behavior; explicit override planned).
2. Live WACP round-trip against a real DEV-TOOLS instance remains the release condition — verify one `PROPERTY_INTELLIGENCE` and one `DESIGN_STUDIO` submission in staging before production traffic.
3. Pre-existing legacy-table drift (missing FKs, type representations) is documented in `Deploy_RC1.md` §7 — intentionally out of scope for this release.

# Copy-ready task: future AIHOME production release

Replace every angle-bracket placeholder.

```text
TASK — AIHOME WIMLOGIC INCREMENTAL PRODUCTION RELEASE

Repository:
D:\ai-cre-wimlogic-v1.0

Product:
- Internal codebase: AI-CRE
- Public product: AI Home Wimlogic
- Public identity: AIHOME.WIMLOGIC

Production:
- SSH: root@74.208.250.229
- SSH key: <SSH_KEY_PATH>
- Application: /opt/ai-home-wimlogic
- Service: ai-home-api.service
- Listener: 127.0.0.1:8030
- Frontend: https://aihome.wimlogic.com
- Backend: https://api-aihome.wimlogic.com
- Health: /health
- Database: ai_cre_wimlogic
- Engine: MariaDB 10.11.16
- Environment: /opt/ai-home-wimlogic/backend/.env
- WACP origin: https://api-dev-tools.wimlogic.com
- WACP application ID: AICRE

Release:
- Version: <RELEASE_VERSION>
- Branch: <RELEASE_BRANCH>
- Candidate commit: <CANDIDATE_COMMIT_OR_TBD>
- Tag: <RELEASE_TAG>
- Frontend deployment: <VERCEL_DEPLOYMENT_OR_PENDING>
- Backend artifact: <BACKEND_ARTIFACT_NAME>
- Migration files: <MIGRATION_FILES_OR_NONE>
- Approved reference data: <REFERENCE_DATA_OR_NONE>
- Approval record: <APPROVAL_RECORD_OR_PENDING>

Read completely:
- docs/deployment/AIHOME_PRODUCTION_BASELINE.md
- docs/deployment/AIHOME_PRODUCTION_DEPLOYMENT_RUNBOOK.md
- docs/deployment/AIHOME_RELEASE_CHECKLIST.md

Objective:
Prepare and, only if explicitly approved, execute an incremental AIHOME
production release.

Use the verified baseline and inspect only changes since the last verified
backend/database/frontend release identities unless read-only checks detect
infrastructure drift. Do not rediscover the complete VPS when the documented
host, service, port, proxy, database, health, WACP, and asset facts still
match.

Required preparation:
1. Audit Git branch, HEAD, ancestry, dirty tracked files, untracked files,
   migrations, tests, frontend configuration, and backend configuration.
2. Preserve unrelated local work. Never package the active dirty repository.
3. Prove ancestry and create a clean release worktree.
4. Classify changes separately as frontend/Vercel, backend/VPS, database,
   WACP, reference data, demo data, or assets.
5. Run frontend `npm ci` and `npm run build` when frontend changes.
6. Verify Vercel team/project, production branch, immutable deployment,
   source commit, Production API-base presence, build logs, and alias.
7. Use `VITE_API_BASE_URL=https://api-aihome.wimlogic.com/api/v1`.
8. Run backend tests and Python compile/import validation.
9. Analyze migrations against the current production 28-table schema.
10. Build a secret-free allowlisted backend artifact from the clean commit.
11. Generate and verify internal and archive SHA-256 manifests.
12. Inspect production read-only only as needed to confirm the baseline and
    release delta.
13. Detect queued/running AIHOME executions and Design Studio jobs.
14. Create new restricted database, backend, environment, and uploaded-assets
    backups.
15. Restore to disposable MariaDB 10.11.16 and rehearse exact migrations,
    reference data, verification, asset handling, and rollback/repair.
16. Freeze the package and production checklist.
17. Stop for approval before production changes unless exact execution
    approval is already present.

Health:
- Authoritative route is `/health`.
- Do not use `/api/v1/health` unless reviewed source intentionally adds it.
- Require loopback and public HTTP 200.

WACP safety:
- Origin must be https://api-dev-tools.wimlogic.com with no path suffix.
- Application ID must be AICRE.
- Never expose WACP_API_KEY or WACP_API_SECRET.
- Never recreate or reuse a missing historical DEV-TOOLS job.
- Terminal executions must stop polling.
- A missing job requires approved terminal disposition, not endless polling.
- Result-sync failure must not resubmit a workflow.
- Provider-free connectivity must pass before any real workflow.
- Real workflow/provider/LLM testing requires separate approval.

Data safety:
- Preserve production schema, business rows, runtime history, reports, assets,
  users, and credentials unless exact changes are approved.
- Never replace production with a full local database dump.
- Design Studio configuration and approved reference data require stable,
  repeatable scripts.
- Demo synchronization is a separate task with local/production comparison,
  stable keys, FK remapping, duplicate prevention, asset manifest/checksums,
  backups, disposable rehearsal, rollback, and separate approval.
- Exclude credentials, provider secrets, users, test jobs, failed development
  runs, local paths, and unrelated development data.

Mandatory stops:
- Unexpected ancestry or infrastructure drift
- Unapproved local changes in release scope
- Wrong Vercel project/branch/commit/environment
- Frontend build or deployment failure
- Artifact hash or secret-scan failure
- Wrong host, service, port, database, engine, health route, or WACP origin
- Backup, asset backup, restore, or migration rehearsal failure
- Schema/data-integrity/foreign-key/duplicate failure
- Backend startup/listener or /health failure
- API, uploaded asset, report, or Design Studio regression
- WACP metadata/authentication failure
- Unexpected polling of a protected terminal job
- Unexpected runnable job, workflow run, provider request, token use, or LLM call
- Need to edit a frozen file or change approved order

Release record:
- Version: <RELEASE_VERSION>
- Branch: <RELEASE_BRANCH>
- Commit: <RELEASE_COMMIT_SHA>
- Tag: <RELEASE_TAG>
- Frontend deployment: <VERCEL_DEPLOYMENT>
- Backend artifact: <BACKEND_ARTIFACT_NAME>
- Artifact SHA-256: <BACKEND_ARTIFACT_SHA256>
- Internal manifest SHA-256: <CONTENT_MANIFEST_SHA256>
- Migration files: <MIGRATION_FILES_OR_NONE>
- Approved reference data: <REFERENCE_DATA_OR_NONE>
- Approval: <APPROVAL_RECORD>
- Deployment timestamp: <UTC_TIMESTAMP>
- Backend backup: <BACKEND_BACKUP_PATH>
- Environment backup: <ENV_BACKUP_PATH>
- Database backup: <DATABASE_BACKUP_PATH>
- Asset backup: <ASSET_BACKUP_PATH>

Report:
- Exact delta from backend, database, and frontend production identities
- Git ancestry and clean-source evidence
- Frontend build and Vercel deployment evidence
- Backend artifact and secret-scan evidence
- Migration/asset rehearsal and rollback feasibility
- Production preflight and exact execution checklist
- Stop conditions or unresolved drift
- Final readiness or deployment result

Do not commit, push, tag, deploy, migrate, restart, reconfigure, transfer demo
data, or initiate a workflow/provider call unless the task explicitly
authorizes that exact action.
```


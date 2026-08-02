# AI Home Wimlogic Release Checklist

Release: `<RELEASE_VERSION>`  
Branch: `<RELEASE_BRANCH>`  
Commit: `<RELEASE_COMMIT_SHA>`  
Tag: `<RELEASE_TAG>`  
Frontend deployment: `<VERCEL_DEPLOYMENT>`  
Backend artifact: `<BACKEND_ARTIFACT_NAME>`  
Artifact SHA-256: `<BACKEND_ARTIFACT_SHA256>`  
Migrations: `<MIGRATION_FILES_OR_NONE>`  
Reference data: `<APPROVED_REFERENCE_DATA_OR_NONE>`  
Approval: `<APPROVAL_RECORD>`

## 1. Scope and Git

- [ ] Read `AIHOME_PRODUCTION_BASELINE.md`.
- [ ] Confirm no infrastructure drift.
- [ ] Record local branch, HEAD, upstream, tags, and status.
- [ ] Classify every tracked and untracked change.
- [ ] Exclude bytecode, dumps, archives, `.env`, credentials, uploads, and unrelated work.
- [ ] Prove candidate ancestry.
- [ ] Build from a clean release worktree.
- [ ] Record frontend/backend/database/WACP/data impact separately.
- [ ] Confirm release commit and tag are intentionally approved and pushed.

## 2. Frontend/Vercel

- [ ] Confirm Vercel team/project and production branch.
- [ ] Confirm Production `VITE_API_BASE_URL` presence.
- [ ] Confirm expected value is `https://api-aihome.wimlogic.com/api/v1` without printing secret values.
- [ ] `npm ci` passes.
- [ ] `npm run build` passes.
- [ ] Production bundle contains no loopback API URL.
- [ ] Terminal polling includes every backend terminal state.
- [ ] Immutable deployment ID/URL and source commit recorded.
- [ ] Immutable deployment returns HTTP 200.
- [ ] Production alias returns HTTP 200.
- [ ] Browser console/network and core UI checks pass.

## 3. Backend

- [ ] Backend tests pass.
- [ ] Python compile/import gate passes.
- [ ] WACP/polling/result-sync tests pass when affected.
- [ ] Design Studio/report/upload tests pass when affected.
- [ ] Allowlist reviewed.
- [ ] Frozen artifact built from clean commit.
- [ ] Internal manifest and archive hashes generated.
- [ ] Every internal hash verifies.
- [ ] Secret/exclusion scan passes.
- [ ] Artifact contains no frontend, `.env`, uploads, dumps, caches, archives, or unrelated docs.

## 4. Database and data

- [ ] Current production schema compared with candidate.
- [ ] Read-only preflight frozen.
- [ ] Forward migration frozen.
- [ ] Required configuration/reference script is repeatable and conflict-safe.
- [ ] Post-migration verification frozen.
- [ ] Rollback/forward-repair procedure frozen.
- [ ] Existing business/runtime/history rows preserved.
- [ ] Design Studio tools/options changes explicitly enumerated.
- [ ] Demo data excluded or separately approved.
- [ ] Full local database replacement is prohibited.

## 5. Production preflight

- [ ] Host/OS/path/service match baseline.
- [ ] Service command and listener are `127.0.0.1:8030`.
- [ ] Database is `ai_cre_wimlogic`, MariaDB 10.11.16.
- [ ] `/health` is registered; `/api/v1/health` is not assumed.
- [ ] OpenLiteSpeed proxy matches baseline.
- [ ] WACP origin is `https://api-dev-tools.wimlogic.com`.
- [ ] WACP application ID is `AICRE`.
- [ ] WACP key/secret presence confirmed without values.
- [ ] Queued/running executions and Design Studio jobs recorded.
- [ ] Upload root/count/size recorded.
- [ ] Disk and memory are sufficient.
- [ ] Production preflight has no `FAIL` or unresolved `REVIEW`.

## 6. Backups and rehearsal

- [ ] New timestamped mode-700 backup directory created.
- [ ] Database dump includes routines, triggers, and events.
- [ ] Dump is non-empty with expected table definitions.
- [ ] Backend/application backup created.
- [ ] Environment backup created with restricted permissions.
- [ ] Uploaded-assets backup created.
- [ ] Non-secret backup sizes and SHA-256 values recorded.
- [ ] Environment backup path/size/owner/permissions recorded without checksum publication.
- [ ] Dump and assets transfer checksums match.
- [ ] Disposable target is confirmed MariaDB 10.11.16 and non-production.
- [ ] Restore succeeds and baseline counts match.
- [ ] Exact migration rehearsal passes.
- [ ] Repeatability/one-time behavior documented.
- [ ] Foreign-key/orphan/duplicate checks pass.
- [ ] Existing data and assets are preserved.
- [ ] Rollback/forward-repair rehearsal passes.

## 7. Approval Gate 2

- [ ] Exact frontend deployment action approved.
- [ ] Exact backend artifact/hashes approved.
- [ ] Exact migration/reference scripts approved.
- [ ] Exact service/configuration actions approved.
- [ ] Exact rollback boundary approved.
- [ ] Maintenance announced.
- [ ] New workflow/Design Studio submissions paused.
- [ ] In-flight execution/job IDs recorded.

## 8. Production execution

- [ ] Frozen preflight retained.
- [ ] AIHOME stopped and confirmed inactive.
- [ ] Only allowlisted backend files deployed.
- [ ] Deployed hashes match.
- [ ] Candidate configuration loads without printing values.
- [ ] Reviewed dependencies installed.
- [ ] Forward migration completes without SQL errors.
- [ ] Reference/configuration data applies exactly as approved.
- [ ] Post-migration verification passes.
- [ ] No demo/runtime/user/credential rows were imported.
- [ ] Frontend deployment is coordinated with backend compatibility.

## 9. Startup and verification

- [ ] `ai-home-api.service` is active/running.
- [ ] MainPID and `127.0.0.1:8030` listener verified.
- [ ] Loopback `/health` returns HTTP 200.
- [ ] Public `/health` returns HTTP 200.
- [ ] Projects/properties APIs return HTTP 200.
- [ ] Property-image API and asset delivery pass.
- [ ] Reports and workflow history/results pass.
- [ ] Design Studio tools/jobs pass.
- [ ] DEV-TOOLS health and WACP metadata return HTTP 200.
- [ ] AICRE authentication passes without exposing credentials.
- [ ] Provider-free rejection passes if separately approved.
- [ ] Protected terminal jobs are not polled again.
- [ ] Result synchronization follows shared `result_sync`.
- [ ] Workflow-run and LLM-call counts are unchanged.
- [ ] Sanitized application/proxy/Vercel logs contain no release error.

## 10. Completion or rollback

- [ ] No mandatory stop condition remains.
- [ ] Before/after schema and critical counts recorded.
- [ ] Asset count/size/hash evidence recorded when assets changed.
- [ ] Evidence files hashed.
- [ ] Evidence-manifest SHA-256 recorded.
- [ ] Deployment timestamp: `<UTC_DEPLOYMENT_TIMESTAMP>`.
- [ ] Backend backup: `<BACKEND_BACKUP_PATH>`.
- [ ] Environment backup: `<ENV_BACKUP_PATH>`.
- [ ] Database backup: `<DATABASE_BACKUP_PATH>`.
- [ ] Asset backup: `<ASSET_BACKUP_PATH>`.
- [ ] Final status is `COMPLETE`, `COMPLETE WITH CONDITIONS`, or `ROLLED BACK`.

## Mandatory stop

Stop on unexpected ancestry, unapproved changes, wrong Vercel identity,
frontend build/deployment failure, artifact/hash/secret failure, wrong
infrastructure, backup/restore/rehearsal failure, schema/data-integrity
failure, backend startup/listener/health failure, API/asset regression, WACP
authentication failure, unexpected polling, or any workflow/provider/LLM
invocation. Preserve evidence; do not alter the frozen release or improvise.


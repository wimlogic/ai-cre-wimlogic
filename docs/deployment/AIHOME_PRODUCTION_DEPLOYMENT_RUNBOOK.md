# AI Home Wimlogic Production Deployment Runbook

## Purpose and product identity

This is the reusable release procedure for:

- internal repository/codebase: **AI-CRE**;
- public product: **AI Home Wimlogic**;
- public identity: **AIHOME.WIMLOGIC**.

Repository: `D:\ai-cre-wimlogic-v1.0`

AIHOME is five coordinated release units. Approval for one does not implicitly
authorize another:

1. frontend release through the Git-connected Vercel project;
2. backend frozen artifact deployed to the VPS;
3. `ai_cre_wimlogic` database migration;
4. WACP configuration/connectivity with DEV-TOOLS;
5. reference or demonstration data and uploaded assets.

## Fixed production topology

| Item | Verified value |
|---|---|
| SSH target | `root@74.208.250.229` |
| Application root | `/opt/ai-home-wimlogic` |
| Backend root | `/opt/ai-home-wimlogic/backend` |
| Backend service | `ai-home-api.service` |
| Backend listener | `127.0.0.1:8030` |
| Public frontend | `https://aihome.wimlogic.com` |
| Public backend | `https://api-aihome.wimlogic.com` |
| Authoritative health route | `/health` |
| Database | `ai_cre_wimlogic` |
| Database engine | MariaDB 10.11.16 |
| Environment file | `/opt/ai-home-wimlogic/backend/.env` |
| WACP origin | `https://api-dev-tools.wimlogic.com` |
| WACP application ID | `AICRE` |

The deployed source registers `GET /health` directly on the FastAPI
application. Do not use `/api/v1/health` unless a future reviewed source change
intentionally adds and tests that route.

## Release record

Complete before the execution approval gate:

| Field | Release value |
|---|---|
| Release version | `<RELEASE_VERSION>` |
| Branch | `<RELEASE_BRANCH>` |
| Commit | `<RELEASE_COMMIT_SHA>` |
| Tag | `<RELEASE_TAG>` |
| Frontend deployment ID/URL | `<VERCEL_DEPLOYMENT>` |
| Backend artifact | `<BACKEND_ARTIFACT_NAME>` |
| Backend artifact SHA-256 | `<BACKEND_ARTIFACT_SHA256>` |
| Content-manifest SHA-256 | `<CONTENT_MANIFEST_SHA256>` |
| Migration files | `<MIGRATION_FILES_OR_NONE>` |
| Reference-data changes | `<APPROVED_REFERENCE_DATA_OR_NONE>` |
| Approval record | `<APPROVAL_RECORD>` |
| Deployment timestamp | `<UTC_DEPLOYMENT_TIMESTAMP>` |
| Backend backup | `<BACKEND_BACKUP_PATH>` |
| Environment backup | `<ENV_BACKUP_PATH>` |
| Database backup | `<DATABASE_BACKUP_PATH>` |
| Uploaded-assets backup | `<ASSET_BACKUP_PATH>` |

## Source and deployment identities

Keep these identities separate:

- **Local development source** — may contain uncommitted or unrelated work.
- **Git release commit/tag** — one clean, reviewed source identity.
- **Vercel deployment** — immutable frontend build tied to an exact commit and
  production environment.
- **Backend frozen artifact** — allowlisted backend files exported from the
  release commit and hashed.
- **VPS backend source** — the exact deployed artifact under
  `/opt/ai-home-wimlogic`.
- **Database state** — schema, configuration/reference rows, business rows,
  runtime history, and assets; it does not equal a Git revision.

The current VPS backend Git checkout and database are intentionally on
different release layers: backend source is RC1 commit `da1a0e5...`, while the
database has the verified RC2 28-table migration state. Future work must
compare both, not assume one commit describes the whole production system.

## Mandatory release lifecycle

```text
local audit
  -> frontend/backend/database/WACP/data impact classification
  -> tests and production builds
  -> migration analysis
  -> intentional commit, push, and tag
  -> Vercel deployment verification
  -> backend frozen artifact, scan, and hashes
  -> production preflight
  -> database/application/environment/assets backups
  -> disposable restore and migration rehearsal
  -> production execution approval
  -> backend deployment and database migration
  -> service start and /health
  -> API and asset regression
  -> WACP, polling, and result-sync verification
  -> rollback or release completion
```

## Phase 1 — local change and ancestry audit

Run from `D:\ai-cre-wimlogic-v1.0`:

```powershell
git status --short --branch
git rev-parse HEAD
git branch --show-current
git remote -v
git log --oneline --decorate -n 30
git diff --stat
git diff --name-status
git diff --cached --name-status
git ls-files --others --exclude-standard
```

Classify every changed and untracked file:

- frontend source/configuration;
- backend source/configuration;
- schema/migration;
- required application configuration;
- Design Studio tools/options;
- reference data;
- demonstration/business data;
- generated assets/reports;
- runtime history;
- tests/fixtures;
- credentials or local environment;
- generated/cache/archive material;
- unrelated work.

The current local worktree contains tracked bytecode and untracked database
dumps/schema/upgrade materials. Never build a release from this active dirty
directory.

Create a clean worktree:

```powershell
git fetch --all --tags --prune
git merge-base --is-ancestor <LAST_VERIFIED_RELEASE_COMMIT> <CANDIDATE_COMMIT>
git worktree add ..\aihome-release-<RELEASE_VERSION> <CANDIDATE_COMMIT>
git -C ..\aihome-release-<RELEASE_VERSION> status --porcelain
git -C ..\aihome-release-<RELEASE_VERSION> rev-parse HEAD
```

Stop on unexpected ancestry, dirty clean-room source, or ambiguous ownership
of any file.

Commit/tag/push only with explicit approval:

```powershell
git switch -c release/<RELEASE_VERSION>
git add -- <explicit-approved-paths>
git diff --cached --check
git diff --cached --name-status
git commit -m "release(aihome): <RELEASE_VERSION>"
git push -u origin release/<RELEASE_VERSION>
git tag -a <RELEASE_TAG> <RELEASE_COMMIT_SHA> -m "AIHOME <RELEASE_VERSION>"
git push origin <RELEASE_TAG>
```

Because Vercel is Git-connected, a push or merge to its configured production
branch can deploy the frontend. Treat that push/merge as a deployment-bearing
action and confirm the Vercel branch policy before executing it.

## Phase 2 — impact classification

Build a release matrix before testing:

| Unit | Changed? | Evidence and action |
|---|---|---|
| Frontend/Vercel | `<YES/NO>` | Build, environment, deployment verification |
| Backend/VPS | `<YES/NO>` | Tests, artifact, service deployment |
| Database | `<YES/NO>` | Preflight/migration/verify/rollback |
| WACP | `<YES/NO>` | Origin, auth, polling/result-sync compatibility |
| Reference/demo/assets | `<YES/NO>` | Separate manifest and approval |

A frontend-only release must not restart the backend. A backend-only release
must not trigger an unrelated Vercel production build. A schema migration must
not be hidden in application startup.

## Phase 3 — frontend build and Vercel release

### Configuration contract

The frontend reads:

```text
VITE_API_BASE_URL
VITE_APP_NAME
VITE_APP_VERSION
```

Production must use:

```text
VITE_API_BASE_URL=https://api-aihome.wimlogic.com/api/v1
```

`frontend/src/config/app.ts` strips `/api/v1` to derive the backend origin for
`/health` and `/uploads`. Do not set the value to the frontend origin or omit
the `/api/v1` suffix.

Do not print Vercel environment values. Confirm names, target environment, and
presence through approved Vercel access.

### Build

From the clean release worktree:

```powershell
Set-Location frontend
npm ci
npm run build
```

Required checks:

- TypeScript/Vite build exits zero;
- no local loopback URL is embedded in production assets;
- production API base is supplied by Vercel;
- frontend polling stops for every backend terminal state;
- uploads resolve from `https://api-aihome.wimlogic.com/uploads/...`;
- projects, properties, images, reports, workflow history, and Design Studio
  views compile.

The current local frontend terminal helper recognizes `Completed`, `Succeeded`,
`Failed`, and `Cancelled`, while the backend also supports
`Completed with Warnings`. Treat this as a required compatibility review for
the next frontend release.

### Vercel verification

The repository has no committed `.vercel/project.json` or `vercel.json`;
therefore do not guess the project, team, branch, or deployment identity.

Before production promotion, record:

- Vercel team/project;
- production branch;
- deployment ID and immutable deployment URL;
- source commit SHA;
- build status/logs;
- production alias assignment;
- `VITE_API_BASE_URL` presence for Production;
- HTTP 200 from `https://aihome.wimlogic.com`;
- visible application version/commit when available;
- browser console/network regression results.

Verify both the immutable deployment URL and the production alias. A successful
Git push is not proof that the correct frontend reached production.

## Phase 4 — backend tests and frozen artifact

From the clean worktree:

```powershell
Set-Location backend
python -m pytest
python -m compileall app wacp
```

Release-specific tests must cover affected payload building, WACP adapter,
polling, result synchronization, reports, Design Studio, asset paths, and
failure handling.

The backend artifact should normally allowlist:

```text
backend/app/**
backend/wacp/**
backend/requirements.txt
```

Include only approved migration/operator files in separate paths. Exclude:

```text
.git/
.env*
*.pem
*.key
*.crt
*.pfx
database dumps and schema snapshots not approved as migrations
archives
__pycache__/
*.pyc
.pytest_cache/
.vscode/
frontend/
Legacy_AIStudio/
uploads/
generated assets and reports
test images and local fixtures
```

Generate a relative-path manifest:

```powershell
$artifactRoot = (Resolve-Path -LiteralPath '<ARTIFACT_ROOT>').Path
$manifestPath = Join-Path $artifactRoot 'ARTIFACT_CONTENT_SHA256.txt'
$lines = Get-ChildItem -LiteralPath $artifactRoot -Recurse -File |
  Where-Object { $_.FullName -ne $manifestPath } |
  Sort-Object FullName |
  ForEach-Object {
    $relative = $_.FullName.Substring($artifactRoot.Length + 1).Replace('\','/')
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash
    "$hash  $relative"
  }
$lines | Set-Content -LiteralPath $manifestPath
Compress-Archive -LiteralPath $artifactRoot -DestinationPath '<BACKEND_ARTIFACT_NAME>'
Get-FileHash -Algorithm SHA256 -LiteralPath '<BACKEND_ARTIFACT_NAME>'
```

Secret scan filenames and content. Review every finding. Never include
credentials, `.env`, WACP secrets, database dumps, uploads, local paths,
nested archives, or unrelated AI-CRE documents.

Approval Gate 1 freezes commit/tag, frontend deployment plan, backend
allowlist/artifact/hashes, migrations, reference data, and checklist.

## Phase 5 — database and data design

Every release with database impact requires frozen:

- read-only production preflight;
- forward migration;
- required configuration/reference-data script;
- post-migration verification;
- rollback or forward-repair plan.

### Data classification

| Class | AIHOME examples | Normal handling |
|---|---|---|
| Schema/migration | Tables, columns, indexes, FKs | Additive reviewed SQL |
| Required application configuration | WACP/app settings | Environment or idempotent rows |
| Design Studio configuration | Tools, options, image requirements | Stable-key reference manifest |
| Approved reference data | Enumerations/rules | Repeatable, conflict-safe seed |
| Demo business data | Projects, properties, property images | Separate approved import |
| Generated assets/reports | Designs, outputs, analysis reports | Preserve; do not seed normally |
| Runtime history | Executions, events, jobs, API usage | Preserve; never replace |
| Development/test data | Fixtures, failed test jobs, local paths | Exclude |
| Users/credentials | Users, API keys, provider/WACP secrets | Never transfer |

A normal release must preserve every existing production business row. Never
replace `ai_cre_wimlogic` with a full local dump.

### Demo-data task

Demo synchronization is separate and requires:

1. local-versus-production row comparison;
2. exact dependency-ordered manifest;
3. stable business keys;
4. safe foreign-key remapping;
5. insert/update/skip conflict decisions;
6. duplicate prevention and repeatability;
7. separate image/file asset manifest;
8. asset size and SHA-256 verification;
9. production and asset backups;
10. disposable MariaDB 10.11 rehearsal;
11. API, image, Property Intelligence, and Design Studio checks;
12. rollback plan and separate production approval.

Do not copy credentials, provider secrets, users, test jobs, runtime history,
failed runs, local paths, or unrelated development data.

## Phase 6 — production read-only preflight

Confirm:

- host, OS, application paths, service, command, and listener;
- database `ai_cre_wimlogic` and MariaDB 10.11.16;
- current backend Git/artifact identity;
- expected schema/table/count baseline;
- uploaded-assets path, count, and size;
- current frontend deployment identity;
- disk and memory;
- OpenLiteSpeed route to port 8030;
- `/health` source registration;
- WACP origin `https://api-dev-tools.wimlogic.com`;
- application ID `AICRE`;
- WACP key/secret presence only;
- queued/running AIHOME executions and in-flight Design Studio work;
- no unexpected infrastructure drift.

Never display, copy, hash into reports, or expose `WACP_API_KEY`,
`WACP_API_SECRET`, database passwords, provider credentials, or Vercel secret
values.

## Phase 7 — backups and disposable rehearsal

Create a new restricted non-overwriting directory:

```bash
umask 077
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_ROOT="/root/production-backups/aihome-${STAMP}"
install -d -m 700 /root/production-backups
mkdir -m 700 "$BACKUP_ROOT"
```

Database:

```bash
mariadb-dump --single-transaction --quick --routines --triggers --events \
  --hex-blob --databases ai_cre_wimlogic \
  > "$BACKUP_ROOT/ai_cre_wimlogic.sql"
test -s "$BACKUP_ROOT/ai_cre_wimlogic.sql"
grep -c '^CREATE TABLE ' "$BACKUP_ROOT/ai_cre_wimlogic.sql"
```

Application, environment, service, and uploaded assets:

```bash
tar -C /opt -czf "$BACKUP_ROOT/aihome-code.tar.gz" ai-home-wimlogic
install -m 600 /opt/ai-home-wimlogic/backend/.env \
  "$BACKUP_ROOT/aihome-backend.env"
systemctl cat ai-home-api.service > "$BACKUP_ROOT/ai-home-api.service.txt"
tar -C /opt/ai-home-wimlogic/backend -czf \
  "$BACKUP_ROOT/aihome-uploads.tar.gz" uploads
chmod 600 "$BACKUP_ROOT"/*
sha256sum "$BACKUP_ROOT/ai_cre_wimlogic.sql" \
  "$BACKUP_ROOT/aihome-code.tar.gz" \
  "$BACKUP_ROOT/aihome-uploads.tar.gz" \
  "$BACKUP_ROOT/ai-home-api.service.txt"
```

The environment backup is secret-bearing. Record path, owner, size, and
permissions, but do not publish its content or checksum in a general report.

Backup readiness requires successful checksum transfer, restore into an
unmistakably disposable MariaDB 10.11.16 target, exact baseline verification,
forward migration, repeatability classification, foreign-key checks,
before/after counts, asset validation, application tests, and rollback or
forward-repair rehearsal.

Approval Gate 2 authorizes the exact backend artifact, migration/reference
scripts, Vercel production action, backup paths, service actions, command
order, WACP checks, and rollback boundary.

## Phase 8 — production execution

Announce maintenance. Pause new workflow and Design Studio submissions.
Record all non-terminal execution/job IDs and current row counts.

Run frozen database preflight before stopping the service. Stop on `FAIL` or
unresolved `REVIEW`.

Stop backend:

```bash
systemctl stop ai-home-api.service
test "$(systemctl is-active ai-home-api.service || true)" = "inactive"
```

Deploy only allowlisted backend files without deleting the prior release:

```bash
cp -a <STAGED_ARTIFACT>/deploy/backend/. /opt/ai-home-wimlogic/backend/
```

Verify every deployed hash. Load configuration from the service working
directory without printing values. Install only reviewed dependencies:

```bash
cd /opt/ai-home-wimlogic/backend
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
```

Run frozen migration, reference data, and post-verification in approved order.
Do not run migration automatically at application startup.

Start:

```bash
systemctl start ai-home-api.service
systemctl show ai-home-api.service \
  -p ActiveState -p SubState -p MainPID -p ExecStart -p WorkingDirectory
ss -ltnp | grep '127.0.0.1:8030'
curl --fail --silent http://127.0.0.1:8030/health
curl --fail --silent https://api-aihome.wimlogic.com/health
```

If frontend changed, verify its immutable Vercel deployment before assigning
or confirming the production alias. Coordinate frontend/backend contract
compatibility so neither version is temporarily incompatible.

## Phase 9 — API, assets, WACP, polling, and result sync

### Existing APIs

Use GET/HEAD only unless a mutation is explicitly approved. Check:

- projects and properties;
- property images and asset delivery;
- property analysis reports;
- workflow executions/events/results;
- Design Studio tools/jobs;
- generated assets;
- release-specific endpoints.

Canonical collection routes may redirect a no-slash URL. Verify the canonical
route returns HTTP 200.

### WACP safety

- Production origin is exactly `https://api-dev-tools.wimlogic.com` with no
  `/wacp/v1` suffix.
- Application ID is exactly `AICRE`.
- Credentials are read directly into process memory and never printed.
- Detect queued/running AIHOME executions before cutover.
- Never recreate, reuse, retry, or synthesize a missing historical DEV-TOOLS
  job automatically.
- Terminal local statuses must stop polling.
- A missing remote job must receive an approved terminal local disposition;
  it must not be polled forever.
- Result retrieval must use the shared `result_sync` path.
- A result-sync failure records `result_sync_error` and must not resubmit the
  remote job.
- Provider-free connectivity must pass before any real workflow approval.
- Real workflow/provider/LLM testing requires separate approval.

Provider-free verification:

1. DEV-TOOLS `/api/v1/health` is HTTP 200.
2. `/wacp/v1/meta` is HTTP 200.
3. AICRE authenticates using a read-only existing rejected job when possible.
4. If separately approved, unassigned-intent submission returns
   HTTP 404 / `WACP-401` / `REJECTED`.
5. The rejected audit job has no workflow template, version, or run.
6. No runnable job, workflow run, provider request, token use, or LLM call is
   created.
7. Poll/event/API-usage counts for protected historical jobs do not increase.

## Mandatory stop conditions

Stop and preserve evidence for:

- unexpected Git ancestry;
- unapproved local changes in release scope;
- wrong Vercel project/branch/commit/environment;
- frontend build or deployment failure;
- artifact or deployed-file hash mismatch;
- secret/excluded file exposure;
- wrong host, service, port, database, engine, health route, or WACP origin;
- backup, transfer, restore, or asset-backup failure;
- disposable migration/rehearsal failure;
- unexpected schema, counts, duplicates, or foreign-key orphans;
- backend configuration/import/startup/listener failure;
- loopback or public `/health` failure;
- existing API, upload, report, or Design Studio regression;
- WACP metadata/authentication/contract failure;
- unexpected polling of a protected terminal job;
- unexpected runnable job, workflow, provider request, token use, or LLM call;
- need to edit a frozen file or change the approved sequence.

## Rollback decision tree

### Frontend failure only

- Do not change backend/database merely because frontend verification failed.
- Restore/promote the prior known-good Vercel deployment.
- Verify the production alias and API base.
- Requires the approved Vercel rollback action.

### Before database migration

- Keep AIHOME stopped.
- Restore prior backend code/environment if changed.
- Start the previous backend and verify `/health` and APIs.

### After migration but before new business/reference rows

- Keep AIHOME stopped.
- Run the frozen rollback only when its preconditions pass and rollback is
  explicitly authorized.
- Restore backend/environment and verify original schema/counts.

### After reference, business, runtime, or asset changes

- Do not run destructive schema rollback automatically.
- Preserve evidence and stop submissions.
- Use separately approved forward repair or full database/assets restoration.

### WACP/configuration failure

- Stop AIHOME.
- Restore the latest restricted environment backup.
- Start and verify the prior `/health`/API state only when rollback approval
  includes the restart.
- Do not modify historical jobs or execution records implicitly.

## Evidence required before success

Retain:

- approvals and UTC timestamps;
- local branch, commit, tag, ancestry, and clean-worktree proof;
- frontend build output, Vercel project/deployment/commit/alias evidence;
- production API-base presence without value leakage;
- backend artifact allowlist, internal hashes, archive hash, and secret scan;
- production target/service/listener/proxy/health evidence;
- database/application/environment/assets backup paths and sizes;
- SHA-256 values for non-secret backups and restore evidence;
- disposable migration/rehearsal/rollback results;
- complete production preflight/migration/post-verification output;
- before/after table and critical business/reference/runtime counts;
- foreign-key/orphan/duplicate checks;
- uploaded asset count/size/hash evidence when assets changed;
- API regression and asset-delivery results;
- WACP metadata/authentication/rejection evidence;
- polling/event/API-usage and result-sync evidence;
- exact before/after workflow-run and LLM-call counts;
- sanitized service, proxy, Vercel, and application logs;
- rollback status or final completion decision;
- evidence-manifest SHA-256.

Declare success only when every mandatory check passes and no unresolved drift
or stop condition remains.


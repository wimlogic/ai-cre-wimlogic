# AI Home Wimlogic Verified Production Baseline

## Scope

Read-only confirmation date: 2026-07-29  
Repository: `D:\ai-cre-wimlogic-v1.0`  
Production: `root@74.208.250.229`

Future releases should inspect only changes since this baseline unless a drift
trigger at the end of this document is detected.

## Product and topology

| Fact | Verified state |
|---|---|
| Internal codebase | AI-CRE |
| Public product | AI Home Wimlogic |
| Public identity | AIHOME.WIMLOGIC |
| OS | Ubuntu 24.04 |
| Application root | `/opt/ai-home-wimlogic` |
| Backend service | `ai-home-api.service` |
| Service state | active/running |
| Working directory | `/opt/ai-home-wimlogic/backend` |
| Command | `.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8030` |
| Listener | `127.0.0.1:8030` |
| Public frontend | `https://aihome.wimlogic.com`, HTTP 200, served by Vercel |
| Public backend | `https://api-aihome.wimlogic.com` |
| Health | `GET /health`, loopback/public HTTP 200 |
| Reverse proxy | OpenLiteSpeed `/` to `http://127.0.0.1:8030` |
| Environment | `/opt/ai-home-wimlogic/backend/.env` |
| Database | `ai_cre_wimlogic` |
| Engine | `10.11.16-MariaDB-ubu2404` |

`/api/v1/health` is not registered. The authoritative route is `/health`.

## Local Git baseline

```text
branch: release/v1.0-rc2
HEAD: 3115418de5e3ba3f3e517484919229122e48d975
tag: aihome-v1.0-rc2
upstream: origin/release/v1.0-rc2
```

The local worktree is dirty:

- tracked Python bytecode changed;
- multiple local database dumps are untracked;
- schema and RC1 upgrade-package material is untracked;
- local patch notes are untracked.

These files are not implicitly approved for a future release. Use a clean
worktree and explicit allowlist.

## Production source/database split

The VPS backend worktree is clean:

```text
branch: main
HEAD: da1a0e5c993809e337aab9c0dd08f3a40db4d7af
tag lineage: aihome-rc1
tracked dirty count: 0
```

The database is already at the verified RC2 migration state. Therefore the
next release delta must compare:

1. production backend commit `da1a0e5...`;
2. local candidate commit/tag;
3. current production 28-table schema;
4. current reference and business counts;
5. current Vercel deployment identity.

Do not infer database state from production Git HEAD.

## Database and asset baseline

| Check | Verified value |
|---|---:|
| Base tables | 28 |
| Projects | 3 |
| Properties | 3 |
| Property images | 18 |
| Property analysis reports | 4 |
| Design Studio jobs | 2 |
| Workflow executions | 32 |
| API usage rows | 426 |
| Uploaded files | 53 |
| Uploaded bytes | 46,138,636 |

Execution 23:

```text
execution: EXE-WIM-1A773442248C
status: Failed
historical remote job: JOB-0000004
```

- exactly one approved `ERROR / Failed` cutover event exists;
- execution 23 currently has 183 event rows;
- historical `JOB-0000004` poll-accounting count is 180;
- `JOB-0000004` remains absent from DEV-TOOLS;
- the terminal execution is no longer polled.

The API-usage total is append-only operational data and may increase due to
approved runtime activity. Future baselines must compare protected-job polling
and business invariants, not assume the global total is static.

## WACP baseline

| Fact | Verified state |
|---|---|
| Origin | `https://api-dev-tools.wimlogic.com` |
| Application ID | `AICRE` |
| API key present | yes, value not inspected |
| API secret present | yes, value not inspected |
| DEV-TOOLS service | active |
| DEV-TOOLS health | HTTP 200 |
| WACP metadata | HTTP 200 |
| Provider-free rejection | HTTP 404 / `WACP-401` / `REJECTED` |
| DEV-TOOLS workflow runs | 9 after verification |
| DEV-TOOLS LLM calls | 18 after verification |
| ZONING assignment | none |

The origin is a server origin only. The WACP SDK appends `/wacp/v1`; never
configure the environment with a `/wacp/v1` suffix.

## Frontend baseline and unresolved identity

The production frontend is HTTP 200 and response headers identify Vercel.
The repository does not contain `.vercel/project.json` or `vercel.json`.

The following facts are not recoverable from the repository alone and must be
captured from Vercel for every release:

- Vercel team/project ID;
- production branch;
- immutable deployment ID/URL;
- source commit SHA;
- production environment-variable presence;
- alias promotion record.

The current exact Vercel deployment commit is therefore an unresolved
evidence item, not an infrastructure failure.

## Source compatibility observations

These are validation requirements, not production modifications:

1. Local frontend terminal polling recognizes `Completed`, `Succeeded`,
   `Failed`, and `Cancelled`; backend polling also treats
   `Completed with Warnings` as terminal. Review before the next frontend
   release to prevent repeated polling.
2. Local RC2 `backend/app/main.py` contains the `/uploads` static mount twice.
   The next backend release must decide and test the intended single
   registration before freezing an artifact.
3. Local `.env.example` uses loopback development values. Production values
   belong in Vercel/VPS environments and must never be copied from examples.

## Existing APIs verified

- `GET /health`: HTTP 200
- projects collection: HTTP 200
- properties collection: HTTP 200
- DEV-TOOLS health: HTTP 200
- WACP metadata: HTTP 200

Future release checks must add property images/assets, reports, workflow
history/results, and Design Studio endpoints when those areas change.

## Last known backups

Latest cutover-era AIHOME backup directory:

```text
/root/production-backups/aihome-wacp-cutover-20260729T100715Z
```

Latest retry-specific environment backup:

```text
/root/production-backups/aihome-wacp-cutover-retry-20260729T101500Z
```

These are evidence and rollback history. Never reuse them as the mandatory
backup for a new release.

## Drift triggers

Perform full rediscovery if any change is found in:

- VPS/OS/SSH identity;
- application/backend path;
- service name, working directory, command, or port 8030;
- public frontend/backend domains;
- Vercel team/project/production branch;
- OpenLiteSpeed proxy;
- health route;
- database name or MariaDB version;
- upload root;
- WACP origin/application identity;
- table baseline or critical data counts;
- production backend commit/artifact identity;
- frontend API-base contract.


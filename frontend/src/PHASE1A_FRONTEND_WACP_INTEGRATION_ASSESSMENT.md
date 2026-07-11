# AI-CRE WIMLOGIC V1.0 — Phase 1A
# Frontend WACP Integration Assessment

**Document Status:** Draft for Approval — no code generated
**Author:** Lead Enterprise React Architect
**Scope:** React frontend only. AI-CRE backend, WACP, DEV-TOOLS WIMLOGIC are treated as locked third-party contracts.
**Sources studied:** `ai-cre-frontend.zip` (full src tree), `ai-cre-backend.zip` (API + service layer, contract verification only), `10_WACP_PROTOCOL_v1_0_2.md`, `20_WACP_SDK_ARCHITECTURE.md`, WACP Client SDK v0.2.0.

---

## 1. Existing Frontend Execution Flow (As-Is)

The current execution experience is a fire-and-forget submission with manual, per-row status syncing. There is no automatic polling, no progress indication, no cancel/retry, and no state survival across refresh.

### 1.1 Submission path

`pages/AIOrchestration.tsx` (435 lines) owns the entire execution UX today:

1. Loads projects (`projectService.list`) and cascading properties (`propertyService.listByProject`).
2. Form collects: project, property, workflow code (5 hardcoded pipelines), priority (Low/Normal/High), optional schedule timestamp, optional custom prompt — the last two packed into `metadata_json`.
3. On submit → `workflowService.submit(payload)` → `POST /api/v1/ai-orchestration/submit` → receives a full `WorkflowExecution` (HTTP 202, status `"Pending"`).
4. Displays a one-shot success banner with `execution_number`, then reloads the execution table once.

### 1.2 Status path

- The execution table has a per-row manual "Sync Status" button → `workflowService.checkStatus(id)` → `GET /api/v1/ai-orchestration/status/{execution_id}` → then reloads the full list.
- Backend verification (read-only): this endpoint is already the correct polling target. When `ENABLE_DEVTOOLS_POLLING` is on, the backend pulls DEV-TOOLS, and on a terminal remote state it runs `result_sync.sync_job_result(...)` — meaning **a single frontend poll is what triggers result/asset hydration**. The frontend never needs to know this; it only needs to poll.

### 1.3 Read-only consumers of execution state

| File | Usage |
|---|---|
| `pages/Dashboard.tsx` | `workflowService.listExecutions({limit:100})` for KPI counts + recent activity feed with `StatusBadge` |
| `pages/WorkflowResults.tsx` | Results list → sections, assets (`generatedAssetService.list({execution_id})`), and parent execution for project/property labels |
| `pages/PropertiesView.tsx` | Per-property execution count in a read-only "Workflow" card (tab of the 10-tab workspace) |
| `pages/GeneratedAssets.tsx` | Asset catalog; refreshes only on search/filter change or manual button |

### 1.4 Current status vocabulary (mismatch found)

- Backend local statuses (Title Case): `Pending`, `Running`, `Completed`, `Failed`.
- `utils/status.ts` `WORKFLOW_STATUS_MAP` (lowercase keys): `pending`, `running`, `succeeded`, `failed`. **`succeeded` never occurs; `Completed` falls through to the capitalized-fallback path with `neutral` variant.** Pre-existing defect, directly in Phase 1A scope since the status map must be extended anyway.
- WACP job state machine (protocol §12): `RECEIVED → VALIDATING → ACCEPTED → QUEUED → RUNNING → COMPLETED | FAILED | CANCELLED`. The frontend will never see WACP states directly — only the AI-CRE backend's local vocabulary — but the status map must be ready for `Queued` and `Cancelled` once the backend's WACP migration surfaces them.

---

## 2. Backend API Contract Available to the Frontend (Verified, Locked)

The frontend consumes **only** these existing AI-CRE endpoints. No new endpoints are invented in Phase 1A.

| Purpose | Endpoint | Notes |
|---|---|---|
| Submit job | `POST /api/v1/ai-orchestration/submit` | 202; returns `WorkflowExecutionResponse` incl. `execution_id`, `execution_number`, `status` |
| Poll status | `GET /api/v1/ai-orchestration/status/{execution_id}` | Returns `{execution_id, status}`; backend performs DEV-TOOLS pull + result sync on terminal |
| Execution detail | `GET /api/v1/workflow-executions/{id}` | Timestamps, error_message, retry_count |
| Execution list | `GET /api/v1/workflow-executions/` | Filters: project_id, property_id, status, search — used for refresh-survival restore |
| Execution timeline | `GET /api/v1/workflow-executions/{id}/events` | Feeds `EnterpriseJobTimeline` |
| Results | `GET /api/v1/workflow-results/`, `/{id}`, `/{id}/sections` | Unchanged |
| Assets | `GET /api/v1/generated-assets/?execution_id=` | Unchanged |

**Explicitly not consumed by the frontend:**
- `POST /api/v1/ai-orchestration/callback` — server-to-server webhook (DEV-TOOLS → AI-CRE). The frontend service layer currently contains a client method for it (§3.3). This is a contract violation to be removed.
- Any WACP endpoint (`/wacp/v1/...`) — per the architecture, only the AI-CRE **backend** speaks WACP, via the Client SDK.

**Contract gap (backend dependency, flagged not invented):** the master prompt lists "Handle cancel/retry UI" as a deliverable, and `WacpClient` exposes `cancel()` / `retry()` — but the AI-CRE backend currently exposes **no cancel or retry endpoint**. See Risk R1. Phase 1A will build the cancel/retry UI **disabled behind a capability check** until the backend endpoint exists, or defer it — decision requested in §11.

---

## 3. Component & Service Inventory

### 3.1 Components/pages requiring modification

| File | Change |
|---|---|
| `pages/AIOrchestration.tsx` | **Rebuild** as Enterprise Job Submission page: job submission form + live job monitor with automatic polling, progress stepper, timeline, terminology change ("Generate Analysis" / "Submit to DEV-TOOLS"). Also migrates this page off inline Tailwind-style utility classes onto the Enterprise CSS architecture (see R3) — unavoidable since the page is being rebuilt |
| `pages/WorkflowResults.tsx` | Accept auto-refresh trigger after job completion; replace ad-hoc status pill markup with `StatusBadge` |
| `pages/GeneratedAssets.tsx` | Expose a refresh path invoked on job completion (no manual page refresh) |
| `pages/Dashboard.tsx` | Terminology only ("Execute Workflow" phrasing → "Generate Analysis"); status badges already correct |
| `utils/status.ts` | Extend `WORKFLOW_STATUS_MAP`: fix `Completed` (success), add `Queued` (info), `Cancelled` (neutral), keep `Pending`/`Running`/`Failed`. Extension of the existing map — no parallel status system |
| `types/index.ts` | Add `EnterpriseJobState` union type + polling-related types. Additive only |
| `services/workflowService.ts` | Canonical execution service (already used by all 4 live pages). Additive: nothing to add for submit/status (already present); cancel/retry methods added only when backend endpoint is confirmed |

### 3.2 Components to retain unchanged (reused by new work)

`StatusBadge` (with extended map — **no new badge component**), `EnterpriseCard`, `EnterpriseTable`, `EnterpriseToolbar`, `LoadingState`, `EmptyState`, `ConfirmDialog` (cancel confirmation), `FormField`, `JsonViewer`, `useToast`/`emitToast` (job notifications — **no new notification system**), `useApiList`, `apiClient`, `EnterpriseLayout`/`Header`/`Sidebar`, `config/app.ts`, all CSS Modules + `tokens.css`. All Projects/Properties/Property Images/Settings pages untouched.

### 3.3 Dead code discovered (removal candidates — approval-gated, verified zero importers)

- `services/aiOrchestration.ts` — duplicate of `workflowService` submit/status **and** exposes a `callback()` client method for the server-to-server webhook. Never imported. Removing it also eliminates the architecture violation.
- `services/workflowExecutions.ts` — duplicate list/get plus `create/update/delete` on executions, which the frontend must never do (executions are created only via orchestrated submit). Never imported.
- `components/Cre*.tsx` (CreDashboard, CreProjects, CreProperties, CreSidebar, CreSettings, CreGeneratedAssets, CreConceptDesign, CreWorkflowScheduler) — legacy pre-migration components, zero importers from `App.tsx` or live pages. Flagged for a separate cleanup approval; **not** removed silently in Phase 1A except where directly execution-related (CreWorkflowScheduler, CreConceptDesign) if you approve.

Removal aligns with "Never duplicate services" and "Remove obsolete execution UI," but each deletion goes through the standard approval gate.

---

## 4. New Reusable Frontend Components (Minimal Set)

Reuse-first review eliminated two of the six candidates from the master prompt:

| Candidate | Decision |
|---|---|
| `EnterpriseJobStatusBadge` | **Not created.** Extending `WORKFLOW_STATUS_MAP` + reusing `StatusBadge type="workflow"` covers it. A second badge system would violate the duplication rule |
| `EnterpriseJobNotification` | **Not created.** `emitToast()` already provides global, contextless notifications |
| `hooks/useEnterpriseJobPolling.ts` | **Create.** Single owner of the polling loop: interval, backoff, terminal-state stop, timeout, tab-visibility pause, cleanup |
| `components/EnterpriseJobProgress.tsx` | **Create.** Horizontal enterprise stepper rendering the status flow of §6.2, CSS Module + tokens |
| `components/EnterpriseJobTimeline.tsx` | **Create.** Renders `/workflow-executions/{id}/events` as an audit timeline |
| `components/EnterpriseJobPanel.tsx` (replaces "EnterpriseJobDialog") | **Create.** Composite monitor (Job ID, badge, progress, timeline, error block, cancel/retry slots) embedded in the rebuilt AI Orchestration page rather than a modal — matches the existing two-column page layout and avoids introducing a new dialog paradigm beyond `ConfirmDialog` |

All four new files: CSS Modules backed by `tokens.css`, no Tailwind, no shadcn, `id` props per Enterprise component conventions.

---

## 5. State Management Changes

### 5.1 Enterprise Job state machine (client-side)

```
Idle → Preparing → Submitting → Pending/Queued → Running
                                      ↓              ↓
                                  Cancelled      Completed → ProcessingResults → Done
                                                     ↓
                                                  Failed (→ Retry available)
```

- `Preparing`/`Submitting` are pure client phases (validation, in-flight POST).
- `Pending/Queued/Running/Completed/Failed/Cancelled` mirror backend truth verbatim — the frontend never invents a status, it renders what the poll returns.
- `ProcessingResults` is a brief client phase after the first terminal poll, covering the results/sections/assets refetch ("Processing Results → Importing Assets" in the master prompt's flow are represented here as one client-side refresh phase, since the backend performs the actual import synchronously inside the status call and exposes no intermediate state for it).

State lives in the rebuilt `AIOrchestration.tsx` via `useEnterpriseJobPolling` — no global store introduced; the app currently has none and one job monitor page does not justify adding one.

### 5.2 Refresh survival

On mount, the page calls `GET /workflow-executions/?status=Pending` and `?status=Running` (existing filters). Any non-terminal execution found resumes polling automatically and repopulates the monitor panel. No localStorage/sessionStorage — backend is the single source of truth, which also survives multi-device use.

---

## 6. Polling Strategy

- **Trigger:** starts immediately after a successful submit, or on mount-restore (§5.2).
- **Endpoint:** `GET /api/v1/ai-orchestration/status/{execution_id}` only — this is deliberate, because this call is what drives backend-side DEV-TOOLS sync and result import.
- **Cadence:** 5s for the first 60s, then 10s, then 20s cap (configurable constants in the hook). Lightweight, no WebSocket.
- **Stop conditions:** `Completed`, `Failed`, `Cancelled`, poll timeout (default 15 min → UI shows "still running, monitoring paused" with manual resume), or unmount.
- **Resilience:** transient network errors do not kill the loop — up to N consecutive failures (default 3) are tolerated with backoff before surfacing an enterprise-friendly error banner; document `visibilitychange` pauses polling in background tabs.
- **On terminal Completed:** enter `ProcessingResults` → refetch execution detail, workflow results, sections, generated assets → emit success toast → `Done`.

### 6.2 Status flow rendered by `EnterpriseJobProgress`

`Preparing Request → Submitting → Queued → Running → Processing Results → Completed`, with `Failed`/`Cancelled` as branch terminals. `Pending` from the backend maps to the "Queued" step visually (label decision confirmed in §11 D3).

---

## 7. UI/UX Impact

- Every "Execute Workflow" / "Launch Pipeline" reference becomes **Generate Analysis** (business context) or **Submit to DEV-TOOLS** (technical context). Affected copy: AIOrchestration page header/CTA/empty states, Dashboard hero copy.
- Enterprise status badges everywhere execution status appears (Dashboard already compliant; WorkflowResults gets migrated to `StatusBadge`).
- Job ID (`execution_number`) prominently displayed after submission and in the monitor panel.
- Error handling: network failure, backend unavailable (existing health-pill pattern respected), submission failure (validation vs. server), polling timeout, cancelled job — all surfaced as enterprise-toned messages; raw exception text never rendered (current page renders `err.message` directly — fixed).
- Navigation, sidebar, page hierarchy, layouts, and all non-execution pages unchanged.

---

## 8. API Consumption Changes (Frontend Service Layer)

| Action | Detail |
|---|---|
| Keep | `workflowService` as the single execution service — submit, checkStatus, listExecutions, getExecution, getExecutionEvents, listResults, getResult, getResultSections all already exist and match the backend exactly |
| Remove (approval-gated) | `services/aiOrchestration.ts`, `services/workflowExecutions.ts` (dead duplicates; one exposes the webhook) |
| Add later (blocked on backend) | `workflowService.cancel(id)` / `retry(id)` — only after backend endpoints are confirmed and delivered |
| No change | `apiClient`, all other domain services |

---

## 9. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | **Cancel/retry has no backend endpoint.** WACP + Client SDK support it; AI-CRE backend does not expose it | Build UI slots capability-gated and hidden by default; raise a Phase 1B-backend work item. Do not fake it client-side |
| R2 | **Status vocabulary drift** when the backend migrates from legacy Enterprise Payload Protocol to the WACP Client SDK — new local statuses (`Queued`, `Cancelled`) may appear | Status map extended now to cover the full expected vocabulary; unknown statuses already fall back gracefully |
| R3 | **Styling inconsistency:** AIOrchestration/Dashboard/WorkflowResults/GeneratedAssets still carry Tailwind-style utility classes from before the CSS Modules migration, while the component library is tokens-based | Rebuilt AIOrchestration lands fully on the Enterprise CSS architecture. Other pages: only execution-related fragments touched are migrated; full page migrations remain out of scope |
| R4 | **Backend polling flag:** with `ENABLE_DEVTOOLS_POLLING=false`, status never advances and results never sync via polling — jobs complete only via webhook | UI timeout copy accounts for this; environment requirement documented in the phase changelog |
| R5 | **Polling load:** naive per-row polling of the history table would multiply requests | Only the active job polls the status endpoint; the history table refreshes via a single list call on job-terminal events and manual refresh |
| R6 | **Result sync latency:** first terminal poll performs the full result import server-side and can be slow | `ProcessingResults` phase communicates this explicitly instead of appearing frozen; the status request is awaited without a client-imposed short timeout |

---

## 10. Recommended Implementation Order (one file per gate)

1. `utils/status.ts` — extend workflow status map (smallest, unblocks everything, fixes live `Completed` badge defect)
2. `types/index.ts` — additive job-state types
3. `hooks/useEnterpriseJobPolling.ts` — polling engine (pure logic, testable in isolation)
4. `components/EnterpriseJobProgress.tsx` + its CSS Module
5. `components/EnterpriseJobTimeline.tsx` + its CSS Module
6. `components/EnterpriseJobPanel.tsx` + its CSS Module
7. `pages/AIOrchestration.tsx` — rebuilt Enterprise Job Submission page wiring 1–6
8. `pages/WorkflowResults.tsx` — StatusBadge adoption + completion-refresh hook-in
9. `pages/GeneratedAssets.tsx` — completion-refresh hook-in
10. `pages/Dashboard.tsx` — terminology pass
11. Deletions (each individually approved): `services/aiOrchestration.ts`, `services/workflowExecutions.ts`, obsolete `Cre*` execution components
12. Phase closeout: changelog, manifest, test notes, ZIP

---

## 11. Decisions Requested Before Implementation

- **D1 (Cancel/Retry):** proceed with capability-gated hidden UI now, or defer entirely until the backend endpoint exists?
- **D2 (Dead code):** approve deletion of the two dead services in this phase? Approve `Cre*` cleanup now or as a separate housekeeping phase?
- **D3 (Status labels):** display backend `Pending` as step label "Queued" in the progress stepper (badge still shows the true backend status), or keep "Pending" everywhere verbatim?
- **D4 (Polling constants):** confirm 5s/10s/20s cadence and 15-minute polling timeout, or supply preferred values.

No code will be generated until this assessment and the decisions above are approved.

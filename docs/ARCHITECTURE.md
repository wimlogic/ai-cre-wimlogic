# AIHOME Architecture

AIHOME is the business application for property, project, image, design, and
analysis workflows. The React/TypeScript frontend calls the FastAPI backend.
The backend owns persistence in MySQL and submits AI work through the vendored
WACP client. DEV-TOOLS WIMLOGIC performs orchestration and provider access;
AIHOME does not call AI providers directly.

## Release boundaries

- `frontend/`: presentation and API clients.
- `backend/app/`: FastAPI routes, services, persistence, and storage.
- `backend/wacp/`: vendored WACP client and contracts.
- `database/migrations/`: forward and rollback database changes.
- `backend/tests/`: service, contract, integration, and workflow validation.

Public APIs, WACP contracts, workflows, and database schema are frozen during
an RC except for approved release-blocking fixes.

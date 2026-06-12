# CLAUDE.md

This file provides guidance to Claude (and Claude Code) when working on this repository.

## Project Overview

**ClearPass Visualizer** is a read-only web application for visualizing Aruba ClearPass Policy Manager
services and troubleshooting Access Tracker records. The core feature is an animated **decision tree**
view that shows how a request flowed through a ClearPass service's policy evaluation
(authentication, role mapping, posture, enforcement, etc.).

### Phase 1 Scope (current)
- Read-only access to ClearPass data via the ClearPass API (no write/config operations).
- Browse Services and Access Tracker records.
- Select an Access Tracker record and render its policy evaluation as an animated decision tree
  (nodes = policy/rule evaluation steps, edges = flow/transitions, animation = step-by-step replay).
- Basic filtering/search of Access Tracker records (by date, endpoint, username, service, result).
- Local caching of fetched data in SQLite to reduce repeated calls to ClearPass and to support
  fast re-rendering of previously viewed records.

### Explicitly Out of Scope (for now)
- Any write operations against ClearPass (no policy edits, no CoA, no endpoint changes).
- User authentication/authorization beyond a simple shared config (multi-user RBAC is a later phase).
- Postgres support (placeholder only — see Database section).
- Real-time streaming/tailing of Access Tracker (poll-based refresh is fine for v1).

## Tech Stack

| Layer            | Technology                          |
|------------------|--------------------------------------|
| Frontend         | TypeScript + React                  |
| Graph/Flow UI    | React Flow                          |
| Backend          | Python (FastAPI)                    |
| ClearPass client | `pyclearpass`                       |
| Validation/Models| Pydantic (v2)                       |
| Database         | SQLite (v1) → Postgres (later, via SQLAlchemy-compatible layer) |
| Packaging        | Docker Compose                      |

## Repository Structure (target)

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entrypoint
│   │   ├── api/                 # API route modules (services, access_tracker, health)
│   │   ├── clearpass/           # pyclearpass wrapper + client config
│   │   ├── models/               # Pydantic models (API schemas)
│   │   ├── db/                   # SQLite models, session, migrations
│   │   ├── decision_tree/        # logic that converts tracker records -> tree structure
│   │   └── core/                 # config, settings, logging
│   ├── tests/
│   ├── pyproject.toml / requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DecisionTree/     # React Flow nodes/edges + animation logic
│   │   │   ├── ServiceList/
│   │   │   └── AccessTrackerTable/
│   │   ├── api/                  # typed API client (generated or hand-written)
│   │   ├── types/                # TS types mirroring Pydantic schemas
│   │   └── App.tsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── CLAUDE.md
```

## Key Domain Concepts

- **Service**: A ClearPass Policy Manager service definition (e.g., "Wireless 802.1X", "Guest Access").
  Each service has an ordered set of policy components (authentication, authorization, role mapping,
  posture, enforcement).
- **Access Tracker record**: A logged authentication/authorization request with its full evaluation
  trail — which service matched, which policies/rules fired, the resulting roles and enforcement
  profile, and the final result (ACCEPT/REJECT/DROP).
- **Decision Tree view**: A derived structure built from an Access Tracker record's evaluation trail.
  Each evaluation stage (service categorization, auth method, role mapping rule, posture check,
  enforcement policy rule) becomes a node; the path actually taken is highlighted/animated in sequence
  to show "how the decision was reached."

## Backend Conventions

- Use **FastAPI** with async route handlers where the ClearPass client supports it; otherwise wrap
  blocking `pyclearpass` calls with `run_in_threadpool`.
- All external-facing data shapes are **Pydantic models** in `backend/app/models/`. Internal ClearPass
  API responses should be mapped into these models at the boundary — don't leak raw ClearPass JSON
  into the API layer.
- Decision tree construction logic lives in `backend/app/decision_tree/` and outputs a Pydantic model
  (e.g., `DecisionTree` with `nodes: list[DecisionNode]` and `edges: list[DecisionEdge]`) that maps
  cleanly to React Flow's `Node`/`Edge` shapes on the frontend.
- ClearPass API credentials/config (base URL, client ID/secret, token) come from environment
  variables / `.env`, loaded via `pydantic-settings`. Never hardcode credentials.
- SQLite is used as a local cache: store fetched Services and Access Tracker records with a
  `fetched_at` timestamp; provide a refresh/poll mechanism rather than always hitting ClearPass live.
- Keep the DB access layer abstracted (SQLAlchemy models + repository-style functions) so swapping
  SQLite → Postgres later is a config change, not a rewrite.

## Frontend Conventions

- React Flow is the graph engine for the Decision Tree view. Custom node types should reflect
  ClearPass evaluation stages (Service Match, Authentication, Role Mapping, Posture, Enforcement,
  Result).
- Animation: render the full tree first (dimmed), then progressively highlight nodes/edges along the
  actual evaluation path in sequence, with play/pause/step controls.
- TypeScript types for API responses should mirror the backend Pydantic models 1:1 — prefer
  generating these from the FastAPI OpenAPI schema (e.g., `openapi-typescript`) over hand-maintaining
  duplicates.
- Keep API calls in `frontend/src/api/` behind small typed functions; components should not call
  `fetch` directly.

## ClearPass Integration Notes

- Use `pyclearpass` for all ClearPass Policy Manager API calls (Services, Access Tracker, etc.).
- Treat all ClearPass calls as **read-only** — only use GET-equivalent endpoints. Do not implement
  any create/update/delete operations against ClearPass in this project.
- Be mindful of ClearPass API rate limits / token expiry — the client wrapper should handle token
  refresh and basic retry/backoff.
- Access Tracker queries can return large result sets — always paginate and default to a sane
  recent time window (e.g., last 24 hours) unless the user filters otherwise.

## Database

- **v1**: SQLite file (e.g., `data/clearpass_visualizer.db`), accessed via SQLAlchemy.
- **Later**: Postgres. Design schema/migrations (e.g., Alembic) so the same models work against
  both backends — avoid SQLite-specific types/features.

## Docker Compose

- `docker-compose.yml` should define at least two services: `backend` (FastAPI/Uvicorn) and
  `frontend` (built React app served via Nginx or Vite preview).
- Mount a volume for the SQLite database file so data persists across container restarts.
- ClearPass connection details and other secrets should be passed via environment variables /
  an `.env` file referenced in compose (not committed to git).

## Development Workflow

- Backend: Python 3.11+, dependencies managed via `requirements.txt` or `pyproject.toml`. Use
  `ruff`/`black` for formatting and `pytest` for tests.
- Frontend: Node LTS, `npm` or `pnpm`, `eslint` + `prettier`.
- Favor small, incremental commits. Follow the `chore/`, `feat/`, `fix/` branch prefix convention
  used in other projects, with PRs for review.

## Open Questions / Future Phases

- Multi-user auth and RBAC (read-only viewers vs. admins).
- Postgres migration path and connection pooling.
- Live/streaming updates to Access Tracker (websockets or polling interval configuration).
- Exporting decision tree views (e.g., as images/PDF) for ticket attachments.

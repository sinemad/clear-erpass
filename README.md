# ClearPass Visualizer

A read-only web application for visualizing Aruba ClearPass Policy Manager services and troubleshooting Access Tracker records. The core feature is an animated **decision tree** view that shows how a request flowed through a ClearPass service's policy evaluation — authentication, role mapping, posture, enforcement, and more.

---

## Features

- **Access Tracker browser** — search and filter authentication/authorization records by date, endpoint, username, service, and result
- **Decision tree view** — step-by-step animated replay of how ClearPass evaluated a specific request (which rules matched, which didn't, what the final result was)
- **Services list** — browse configured Policy Manager services
- **Settings UI** — configure the ClearPass server URL and API token directly from the browser; no `.env` editing required
- **Local SQLite cache** — fetched data is cached locally to reduce load on ClearPass and support fast re-rendering of previously viewed records

> **Read-only by design.** This tool only performs GET-equivalent operations against ClearPass. No policies, endpoints, or configurations are modified.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | TypeScript · React 18 · React Flow · React Router v6 |
| Backend | Python 3.11 · FastAPI · Pydantic v2 |
| ClearPass client | pyclearpass |
| Database | SQLite (via SQLAlchemy) |
| Packaging | Docker · Docker Compose |

---

## Quick Start (Docker)

**Prerequisites:** Docker and Docker Compose installed.

```bash
# 1. Clone the repo
git clone https://github.com/your-org/clear-erpass.git
cd clear-erpass

# 2. Start the stack
docker compose up --build
```

Open **http://localhost** in your browser, then navigate to **Settings** and enter your ClearPass server URL and API token. That's it — no `.env` file required for the basic setup.

The backend API is available at **http://localhost:8000**. Interactive API docs (Swagger UI) are at **http://localhost:8000/docs**.

---

## Local Development

### Prerequisites

- Python 3.11 (Homebrew: `brew install python@3.11`)
- Node.js LTS (`brew install node`)

### Backend

```bash
cd backend

# Create and activate a virtual environment
/opt/homebrew/opt/python@3.11/bin/python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the dev server (hot-reload enabled)
uvicorn app.main:app --reload
```

The backend starts at **http://localhost:8000**. The SQLite database is created automatically at `./data/clearpass_visualizer.db` on first run.

> **Optional:** copy `.env.example` to `.env` and fill in your ClearPass credentials if you prefer environment-variable configuration over the Settings UI.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend starts at **http://localhost:5173**. API requests to `/api/*` are proxied to the backend at `localhost:8000` via the Vite dev-server proxy — no CORS configuration needed during development.

---

## Configuration

ClearPass connection settings can be saved in two ways:

### Settings UI (recommended)

Navigate to **http://localhost/settings** (or `http://localhost:5173/settings` in dev mode) and fill in:

| Field | Description |
|---|---|
| ClearPass Server URL | Base URL of your CPPM instance, e.g. `https://clearpass.corp.example.com` |
| API Token | A ClearPass OAuth2 client credentials token with read access |
| Verify SSL | Uncheck only for self-signed certificates in lab environments |

Settings are persisted in the local SQLite database and survive container restarts.

### Environment variables

Copy `.env.example` to `.env` and set the variables before starting the stack. Environment-variable values are used as a fallback when no Settings UI config exists yet.

```bash
cp .env.example .env
```

```env
CLEARPASS_BASE_URL=https://clearpass.corp.example.com
CLEARPASS_API_TOKEN=your-api-token-here
CLEARPASS_VERIFY_SSL=true
DB_PATH=/data/clearpass_visualizer.db
```

---

## API Reference

The backend exposes a self-documenting OpenAPI interface at **http://localhost:8000/docs**.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Liveness check |
| `GET` | `/api/config` | Read current ClearPass connection config |
| `PUT` | `/api/config` | Save ClearPass connection config |
| `GET` | `/api/services` | List all Policy Manager services |
| `GET` | `/api/services/{service_id}` | Get a single service |
| `GET` | `/api/access-tracker` | List Access Tracker records (filterable) |
| `GET` | `/api/access-tracker/{record_id}/decision-tree` | Get the decision tree for a record |

### Access Tracker query parameters

| Parameter | Type | Description |
|---|---|---|
| `start_time` | ISO 8601 datetime | Filter records on or after this time |
| `end_time` | ISO 8601 datetime | Filter records on or before this time |
| `service_name` | string | Exact service name match |
| `username` | string | Filter by identity/username |
| `result` | string | `ACCEPT`, `REJECT`, or `DROP` |
| `limit` | integer (1–200) | Page size, default 50 |
| `offset` | integer | Pagination offset, default 0 |

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── api/
│   │   │   ├── access_tracker.py    # Access Tracker + decision-tree routes
│   │   │   ├── config.py            # Settings read/write routes
│   │   │   ├── health.py            # Health check
│   │   │   └── services.py          # ClearPass services routes
│   │   ├── clearpass/
│   │   │   └── client.py            # pyclearpass wrapper (read-only)
│   │   ├── core/
│   │   │   └── config.py            # pydantic-settings (env-var config)
│   │   ├── db/
│   │   │   ├── models.py            # SQLAlchemy models (AppSettings)
│   │   │   └── session.py           # Engine, session factory, get_db dependency
│   │   ├── decision_tree/
│   │   │   └── builder.py           # Converts raw ClearPass records → DecisionTree
│   │   └── models/
│   │       ├── access_tracker.py    # AccessTrackerSummary Pydantic model
│   │       ├── config.py            # ConfigRead / ConfigUpdate Pydantic models
│   │       └── decision_tree.py     # DecisionTree / DecisionNode / DecisionEdge models
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── config.ts            # Typed fetch wrappers for /api/config
│   │   ├── components/
│   │   │   ├── AccessTrackerTable/  # (placeholder)
│   │   │   ├── DecisionTree/        # (placeholder)
│   │   │   ├── ServiceList/         # (placeholder)
│   │   │   └── Settings/
│   │   │       └── SettingsPage.tsx # ClearPass connection settings form
│   │   ├── types/
│   │   │   └── decisionTree.ts      # TS types mirroring backend Pydantic models
│   │   ├── App.tsx                  # Router + nav layout
│   │   └── main.tsx                 # React entry point
│   ├── package.json
│   └── Dockerfile
├── data/                            # SQLite database volume (gitignored at *.db)
├── docker-compose.yml
├── .env.example
└── CLAUDE.md                        # AI assistant guidance for this repo
```

---

## Decision Tree

The decision tree is the central visualization. For a given Access Tracker record it shows:

1. **Service Match** — which service categorization rule matched the request
2. **Authentication** — method used (EAP-PEAP, EAP-TLS, PAP, etc.) and identity source
3. **Role Mapping** — which rule assigned a role to the endpoint/user
4. **Posture** (if applicable) — health check result
5. **Enforcement** — which enforcement profile was applied
6. **Result** — final decision (`ACCEPT` / `REJECT` / `DROP`)

Nodes that were **not** reached for this request are rendered dimmed. The actual path taken is animated step-by-step with play/pause/step controls.

### Data model

```
DecisionTree
├── record_id, service_name, request_timestamp, final_result
├── nodes: DecisionNode[]
│   └── id, type, position, data: { label, stage, status, summary, details, timestamp }
├── edges: DecisionEdge[]
│   └── id, source, target, label, order, animated
└── path: string[]   ← ordered node IDs of the actual traversal
```

---

## Development Status

This project is in **Phase 1** — the infrastructure and data models are in place but the ClearPass API integration (`client.py`) and frontend views (Access Tracker table, Decision Tree canvas) are not yet implemented. The next steps are:

1. Inspect a real Access Tracker record JSON to confirm field names, then fill in the `TODO` stubs in [`backend/app/clearpass/client.py`](backend/app/clearpass/client.py) and [`backend/app/decision_tree/builder.py`](backend/app/decision_tree/builder.py)
2. Build the Access Tracker table component
3. Build the React Flow decision tree canvas and animation controller

See [`CLAUDE.md`](CLAUDE.md) for full architectural decisions and conventions.

---

## License

See [LICENSE](LICENSE).

# Implementation Plan: Python Interpreter, Full Docker Stack, Environment Files & End-to-End API Integration

Configure Python 3.12 virtual environment, create complete Docker setup (frontend Dockerfile, updated docker-compose.yml), complete environment configurations (.env & .env.example for root and frontend), and ensure all backend and frontend API integrations are robustly linked and tested.

## User Review Required

> [!NOTE]
> Python 3.12.10 has already been installed on your Windows machine via winget (`C:\Users\Egami\AppData\Local\Programs\Python\Python312\python.exe`). We will configure a project virtual environment (`.venv`) using this interpreter and set up `.vscode/settings.json` so your IDE automatically defaults to Python 3.12.

> [!IMPORTANT]
> In `docker-compose.yml`, both `backend` (FastAPI, port 8000) and `frontend` (Vite dev server, port 5173) will be orchestrated with automatic volume hot-reloading and health checks.

## Proposed Changes

### Python Interpreter & Environment Configuration

- Create a `.venv` virtual environment in `geosatalite` using Python 3.12:
  `C:\Users\Egami\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv`
- Install all backend requirements (`requirements.txt`) into `.venv`.
- Create/update `.vscode/settings.json` specifying:
  `"python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe"`

---

### Docker Configuration

#### [NEW] [frontend/Dockerfile](file:///c:/Users/Egami/Downloads/sih/geosatalite/frontend/Dockerfile)
- Multi-stage Dockerfile:
  - Base `node:20-alpine`
  - Development stage (`target: dev`) running `npm run dev -- --host 0.0.0.0 --port 5173`
  - Production stage (`target: prod`) building dist and serving with lightweight nginx / preview

#### [NEW] [frontend/.dockerignore](file:///c:/Users/Egami/Downloads/sih/geosatalite/frontend/.dockerignore)
- Ignore `node_modules`, `dist`, `.git`, `.env.local` to optimize Docker build context.

#### [MODIFY] [docker-compose.yml](file:///c:/Users/Egami/Downloads/sih/geosatalite/docker-compose.yml)
- Add `frontend` service:
  - Context: `./frontend`
  - Container name: `satquery-frontend`
  - Ports: `5173:5173`
  - Volume mount for hot-reloading: `./frontend:/app` and anonymous `/app/node_modules`
  - Depends on `backend` healthcheck
  - Connected to `satquery-network`
- Ensure `backend` service uses `.env`, port `8000:8000`, volume mounts for `./backend:/app/backend`.

---

### Environment Variables (.env & .env.example)

#### [MODIFY] [.env](file:///c:/Users/Egami/Downloads/sih/geosatalite/.env)
- Add complete documentation and variables for NASA APOD API, NVIDIA DeepSeek, and NVIDIA Nemotron Parse 2.0 alongside existing CORS, PORT, and mock flags.

#### [MODIFY] [.env.example](file:///c:/Users/Egami/Downloads/sih/geosatalite/.env.example)
- Mirror all variables with clear comments and placeholder values.

#### [NEW] [frontend/.env](file:///c:/Users/Egami/Downloads/sih/geosatalite/frontend/.env)
- Set `VITE_BACKEND_URL=http://localhost:8000` for standalone Vite dev server execution.

#### [NEW] [frontend/.env.example](file:///c:/Users/Egami/Downloads/sih/geosatalite/frontend/.env.example)
- Example template for frontend environment variables.

---

### API Integration & Configuration Refinements

#### [MODIFY] [frontend/vite.config.js](file:///c:/Users/Egami/Downloads/sih/geosatalite/frontend/vite.config.js)
- Configure dev server host `0.0.0.0`, port `5173`.
- Configure dev proxy `/api` and `/query` to `http://localhost:8000` (or `process.env.VITE_BACKEND_URL`) to eliminate any potential CORS friction during local or container development.

#### [MODIFY] [backend/services/chatbot_service.py](file:///c:/Users/Egami/Downloads/sih/geosatalite/backend/services/chatbot_service.py)
- Lower the API timeout from 60s to 12s so queries never hang or freeze if NVIDIA's external API is slow or unreachable.
- Add graceful fallback if `openai` package is missing or fails.

#### [MODIFY] [backend/services/controller.py](file:///c:/Users/Egami/Downloads/sih/geosatalite/backend/services/controller.py)
- Ensure DeepSeek response synthesis in `execute_query` fails soft (if NVIDIA times out or fails, preserve the specialist tool's output immediately without delay).

#### [MODIFY] [frontend/src/services/api.js](file:///c:/Users/Egami/Downloads/sih/geosatalite/frontend/src/services/api.js)
- Export `BACKEND_BASE` so other components (`ReportsPage.jsx`, `ReportExport.jsx`) can import it directly instead of duplicating the fallback logic.

---

## Verification Plan

### Automated Tests
1. Verify Python 3.12 virtual environment:
   `.\.venv\Scripts\python.exe --version`
2. Test backend imports and pipeline:
   `.\.venv\Scripts\python.exe test_backend.py`
3. Run backend server and execute endpoint test suite:
   `.\.venv\Scripts\python.exe test_endpoints.py`
4. Verify frontend build:
   `cd frontend && npm run build`
5. Test Docker compose configuration:
   `docker compose config`
6. Verify Docker build:
   `docker compose build`

### Manual Verification
1. Start full Docker stack (`docker compose up -d`) or local servers.
2. Verify:
   - Backend responds at `http://localhost:8000/health` and `http://localhost:8000/`
   - Tools endpoint returns all 5 specialists at `http://localhost:8000/api/tools`
   - Frontend runs and renders at `http://localhost:5173/`
   - Query workspace `/query` executes queries and shows traces and reports.

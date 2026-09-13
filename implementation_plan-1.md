# SatQuery AI — Full Implementation Plan

Build the complete SatQuery AI system as specified in [SatQuery_AI_Build_Guide.md](file:///c:/Users/Egami/Downloads/sih/geosatalite/SatQuery_AI_Build_Guide.md): an agentic vision-language assistant for multimodal remote sensing image analysis.

## Current State

The frontend already has a solid foundation:
- **3D Earth Globe** (Three.js + @react-three/fiber) with atmosphere shader, clouds, night lights, markers
- **Side Panel** with chat interface, telemetry HUD, quick prompts
- **Search/Navigation** with geocoding (Nominatim), fly-to animation, quick locations
- **API service layer** with geocoding, Overpass, elevation, weather, backend query stub
- **State management** via React Context + useReducer

## What Needs to Be Built

The build guide requires **two major parts**: a Python FastAPI backend (the agentic RS pipeline) and significant frontend additions (upload/compatibility screen, query workspace, execution trace panel, report export). Since ML model training/fine-tuning requires specific GPU hardware and datasets that aren't available here, I'll build the **complete application architecture** with realistic demo/mock inference so the pipeline is fully functional and ready to swap in real models.

---

## Proposed Changes

### Part 1 — Python Backend (FastAPI Agentic Pipeline)

#### [NEW] `backend/requirements.txt`
Dependencies: `fastapi`, `uvicorn`, `python-multipart`, `Pillow`, `rasterio`, `numpy`, `pydantic`, `reportlab`, `python-dotenv`

#### [NEW] `backend/main.py`
FastAPI application entry point with CORS middleware, all API routes mounted.

#### [NEW] `backend/config.py`
Configuration: model registry paths, supported formats, confidence thresholds.

#### [NEW] `backend/models/tool_registry.py`
The **tool/model registry** — JSON-schema-based registry of specialist models (VQA, captioning/grounding, change detection, optical-SAR fusion) as specified in Section 6 of the build guide. Each tool entry defines: `tool_id`, `task_type`, `accepts` (input_type, modality, formats), `parameters`, `outputs`.

#### [NEW] `backend/models/specialists.py`
**Specialist model wrappers** — Adapter classes for each model type (VQA, Captioning, Grounding, ChangeVQA, FusionAnalysis). Initially mock implementations that return structured demo responses with realistic confidence scores. Designed so real model inference (GeoChat, RemoteCLIP, etc.) can be plugged in by replacing the `predict()` method.

#### [NEW] `backend/services/input_checker.py`
**Input Compatibility Checker** — validates:
- File format (GeoTIFF/TIFF vs PNG/JPEG)
- Image count and pairing (single, bi-temporal pair, optical+SAR pair)
- Modality detection (optical RGB, multispectral, SAR)
- Basic metadata extraction (dimensions, bands, CRS if GeoTIFF)
- Co-registration/pairing validation

#### [NEW] `backend/services/controller.py`
**Agentic Controller** — the core orchestrator:
1. Interprets the query text (keyword classification + intent detection)
2. Classifies task type (VQA, captioning, grounding, change_vqa, fusion)
3. Calls the Input Compatibility Checker
4. Selects tool(s) from the registry
5. Configures permitted parameters
6. Executes specialist model(s)
7. Returns structured result with execution trace

#### [NEW] `backend/services/aggregator.py`
**Output Aggregator + Confidence Estimator** — merges outputs from specialist models, computes confidence (softmax margin approach), combines textual and spatial evidence.

#### [NEW] `backend/services/trace_builder.py`
**Execution Trace Builder** — produces the auditable JSON execution summary (task, model/tool names, parameters, outputs, confidence, evidence references) as specified in Section 6.

#### [NEW] `backend/services/report_generator.py`
**Report Generator** — creates downloadable PDF/HTML reports using ReportLab, bundling query, answer, evidence images, and execution trace.

#### [NEW] `backend/routes/upload.py`
`POST /api/upload` — file upload with validation, returns metadata or compatibility error.

#### [NEW] `backend/routes/query.py`
`POST /api/query` — the main pipeline endpoint: receives `{query, image_refs[]}`, runs the full controller pipeline, returns answer + evidence + trace.

#### [NEW] `backend/routes/tools.py`
`GET /api/tools` — lists the current model/tool registry.

#### [NEW] `backend/routes/trace.py`
`GET /api/trace/{query_id}` — re-fetches a past execution trace.

#### [NEW] `backend/routes/report.py`
`GET /api/report/{query_id}` — downloadable PDF/HTML report.

---

### Part 2 — Frontend Enhancements

#### [NEW] `frontend/src/components/UploadWorkspace.jsx`
**Upload & Compatibility screen** — drag-and-drop zone for images/GeoTIFFs, surfaces the Input Compatibility Checker's output (detected modality, format, image count, co-registration status, rejection reasons).

#### [NEW] `frontend/src/components/QueryWorkspace.jsx`
**Query Workspace** — the analysis view with:
- Natural-language query box with autocomplete suggestions from representative query patterns
- Image/map viewer panel for uploaded imagery
- Bounding-box/change-map overlay for evidence
- Confidence indicator (percentage + traffic-light color)

#### [NEW] `frontend/src/components/ExecutionTrace.jsx`
**Execution Trace Panel** — renders the JSON execution trace in a readable, expandable format. Shows: task selected, tool/model used, parameters, outputs, confidence — directly demonstrating the "auditable execution summary" requirement.

#### [NEW] `frontend/src/components/ReportExport.jsx`
**Report Export** — one-click PDF/HTML report download button, calls `/api/report/{query_id}`.

#### [NEW] `frontend/src/components/Navigation.jsx`
**Page Navigation** — tab/nav bar to switch between Home (3D Earth), Upload, Query Workspace, and Reports views.

#### [MODIFY] [App.jsx](file:///c:/Users/Egami/Downloads/sih/geosatalite/frontend/src/App.jsx)
Add client-side routing (react-router-dom) to support four workspaces: Home, Upload, Query, Reports.

#### [MODIFY] [useAppStore.jsx](file:///c:/Users/Egami/Downloads/sih/geosatalite/frontend/src/store/useAppStore.jsx)
Extend state with: `currentPage`, `uploadValidation`, `executionTrace`, `queryHistory`, `activeQueryId`.

#### [MODIFY] [api.js](file:///c:/Users/Egami/Downloads/sih/geosatalite/frontend/src/services/api.js)
Add API calls for: `/api/upload`, `/api/query` (updated), `/api/tools`, `/api/trace/{id}`, `/api/report/{id}`.

---

### Part 3 — Dependencies

#### [MODIFY] [package.json](file:///c:/Users/Egami/Downloads/sih/geosatalite/frontend/package.json)
Add `react-router-dom` for client-side routing.

---

## User Review Required

> [!IMPORTANT]
> **ML Models are mocked**: Since training/fine-tuning RS models (RemoteCLIP, GeoChat, etc.) requires GPU compute, specific datasets (BigEarthNet, RSVQA, CDVQA), and significant time, the specialist models will use **realistic mock inference** that returns properly structured responses. The architecture is designed so real models can be plugged in by implementing the `predict()` method on each specialist class.

> [!IMPORTANT]
> **React Router**: The current app has no routing. I'll add `react-router-dom` for multi-page navigation (Home / Upload / Query / Reports). This adds a dependency.

## Open Questions

> [!IMPORTANT]
> 1. **Grounding vs Captioning**: The build guide says pick one. The guide recommends **grounding** (bounding-box overlay on map) for demo impact. Should I implement grounding, or do you prefer captioning?
> 2. **Report format**: PDF (via ReportLab on backend) or HTML-only reports? PDF requires the `reportlab` Python package.
> 3. **Do you want me to set up a basic Python virtual environment** and install backend dependencies, or just create the files for now?

## Verification Plan

### Automated Tests
- `cd frontend && npm run build` — verify frontend compiles without errors
- `cd backend && python -m pytest` — verify backend unit tests pass (for input checker, controller, trace builder)

### Manual Verification
- Start backend (`uvicorn backend.main:app --reload`) and frontend (`npm run dev`)
- Navigate through all 4 workspaces (Home → Upload → Query → Reports)
- Upload a test image, run a query, inspect execution trace, download report
- Verify demo mode works end-to-end without real ML models

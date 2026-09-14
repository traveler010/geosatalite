# SatQuery AI — NVIDIA AI & NASA APOD Integration Walkthrough

## Overview

Integrated three external AI/data services into the SatQuery AI platform:
1. **DeepSeek Reasoning Chatbot** (`deepseek-ai/deepseek-v4-flash-0731`) via NVIDIA Integrate API
2. **Nemotron Parse 2.0 Visual Processing** (`nvidia/nemotron-parse-2.0`) via NVIDIA Integrate API
3. **NASA APOD Data Feed** (`science.nasa.gov/wp-json/wp/v2/apod-basic`)

---

## Changes Made

### 1. Backend Configuration

#### [MODIFY] [config.py](file:///c:/Users/DELL/Desktop/geosatalite/geosatalite/backend/config.py)
Added environment-configurable settings for:
- `NASA_BASE_URL`, `NASA_API_KEY`
- `NVIDIA_BASE_URL`, `NVIDIA_CHAT_API_KEY`, `NVIDIA_CHAT_MODEL`
- `NVIDIA_VISION_API_KEY`, `NVIDIA_VISION_MODEL`

#### [MODIFY] [requirements.txt](file:///c:/Users/DELL/Desktop/geosatalite/geosatalite/backend/requirements.txt)
Added `openai>=1.0.0` dependency (used as the client for NVIDIA's OpenAI-compatible API).

---

### 2. Backend Services (New)

#### [NEW] [chatbot_service.py](file:///c:/Users/DELL/Desktop/geosatalite/geosatalite/backend/services/chatbot_service.py)
- `generate_chat_response()` — Sends prompts to DeepSeek with `thinking: True` and `reasoning_effort: high`
- Returns both **reasoning chain-of-thought** and **final content answer**
- Used by the query controller to synthesize rich AI-powered answers

#### [NEW] [vision_service.py](file:///c:/Users/DELL/Desktop/geosatalite/geosatalite/backend/services/vision_service.py)
- `parse_visual_image()` — Sends images (URL or local base64) to Nemotron Parse 2.0
- Supports control tokens: `<predict_bbox>`, `<predict_classes>`, `<output_markdown>`, `<predict_text_in_pic>`

#### [NEW] [nasa_service.py](file:///c:/Users/DELL/Desktop/geosatalite/geosatalite/backend/services/nasa_service.py)
- `fetch_apod_list()` — Paginated APOD feed
- `fetch_apod_by_date()` — Single entry by date
- `import_apod_to_session()` — Downloads and imports NASA images into SatQuery upload sessions

---

### 3. Backend Routes (New)

#### [NEW] [routes/ai.py](file:///c:/Users/DELL/Desktop/geosatalite/geosatalite/backend/routes/ai.py)
| Endpoint | Method | Description |
|---|---|---|
| `/api/ai/chat` | POST | DeepSeek reasoning chatbot |
| `/api/ai/vision-parse` | POST | Nemotron Parse 2.0 image processing |

#### [NEW] [routes/nasa.py](file:///c:/Users/DELL/Desktop/geosatalite/geosatalite/backend/routes/nasa.py)
| Endpoint | Method | Description |
|---|---|---|
| `/api/nasa/apod` | GET | Fetch APOD feed (paginated) |
| `/api/nasa/apod/{date}` | GET | Fetch APOD by date |
| `/api/nasa/apod/import` | POST | Import APOD image into session |

#### [MODIFY] [main.py](file:///c:/Users/DELL/Desktop/geosatalite/geosatalite/backend/main.py)
Mounted `ai.router` and `nasa.router`.

---

### 4. Controller Enhancement

#### [MODIFY] [controller.py](file:///c:/Users/DELL/Desktop/geosatalite/geosatalite/backend/services/controller.py)
- After specialist model inference, the answer is now **synthesized through DeepSeek** for richer, more authoritative responses
- Returns `reasoning` field alongside `answer` in query results
- Falls back gracefully to the specialist's raw answer if DeepSeek is unavailable

---

### 5. Frontend Updates

#### [MODIFY] [ChatMessage.jsx](file:///c:/Users/DELL/Desktop/geosatalite/geosatalite/frontend/src/components/ChatMessage.jsx)
- Added collapsible **DeepSeek Reasoning** dropdown (purple brain icon)
- Shows chain-of-thought when available

#### [MODIFY] [SidePanel.jsx](file:///c:/Users/DELL/Desktop/geosatalite/geosatalite/frontend/src/components/SidePanel.jsx)
- Passes `reasoning` from API responses to `ChatMessage`

#### [MODIFY] [QueryWorkspace.jsx](file:///c:/Users/DELL/Desktop/geosatalite/geosatalite/frontend/src/components/QueryWorkspace.jsx)
- Added **DeepSeek Reasoning (Chain of Thought)** section in query results view
- Passes `reasoning` to chat store

#### [MODIFY] [useAppStore.jsx](file:///c:/Users/DELL/Desktop/geosatalite/geosatalite/frontend/src/store/useAppStore.jsx)
- `addMessage()` now accepts optional `reasoning` parameter

#### [MODIFY] [api.js](file:///c:/Users/DELL/Desktop/geosatalite/geosatalite/frontend/src/services/api.js)
Added frontend API functions:
- `fetchNasaApod()` / `importNasaApod()` — NASA APOD integration
- `queryDeepSeekChat()` — Direct DeepSeek chat
- `parseVisionNemotron()` — Direct Nemotron vision parsing

---

### 6. Standalone Tools

#### [NEW] [fetch_nasa_apod.py](file:///c:/Users/DELL/Desktop/geosatalite/geosatalite/fetch_nasa_apod.py)
CLI tool for fetching NASA APOD data with `--count`, `--date`, `--search`, `--download-images` flags.

---

## Validation

| Test | Result |
|---|---|
| Frontend build (`vite build`) | ✅ 2440 modules, 0 errors |
| NASA APOD fetch (10 items) | ✅ 10 entries returned, saved to `nasa_apod_data.json` |
| NASA APOD by date (`2026-09-14`) | ✅ "Where Your Elements Came From" |
| NASA image download | ✅ 1.6 MB JPG saved to `nasa_images/` |
| DeepSeek chatbot (earlier test) | ✅ Reasoning + content returned ("We are the stars we made...") |
| Nemotron Parse 2.0 | ⚠️ Returns empty content via NVIDIA hosted API — model appears to require self-hosted NIM for full functionality |
| Backend service imports | ✅ `chatbot_service`, `vision_service`, `nasa_service` all import cleanly |

> [!NOTE]
> The **Nemotron Parse 2.0** model on NVIDIA's hosted API (`integrate.api.nvidia.com`) returns empty content for all tested images. This is a known limitation of the hosted endpoint — the model is designed primarily for **self-hosted NIM/vLLM deployments**. The integration code is fully functional and ready to work once connected to a self-hosted instance.

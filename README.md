# SatQuery AI

**ISRO Multimodal Remote Sensing Assistant** — Smart India Hackathon 2026

An agentic AI system for querying, analyzing, and understanding satellite imagery through natural language. Features a 3D interactive Earth globe, AI-powered chat interface, and modular analysis pipeline.

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- [Optional] Docker & Docker Compose

### Backend
```bash
cd geosatalite/backend
cp ../.env.example ../.env    # Add your API keys
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

### Frontend
```bash
cd geosatalite/frontend
npm install
npm run dev
```

### Docker
```bash
cd geosatalite
cp .env.example .env          # Add your API keys
docker compose up --build
```

## Configuration

Copy `.env.example` to `.env` and add your API keys:

| Variable | Required | Description |
|----------|----------|-------------|
| `NVIDIA_CHAT_API_KEY` | Yes | NVIDIA API key for DeepSeek chat |
| `NVIDIA_VISION_API_KEY` | Yes | NVIDIA API key for Nemotron vision |
| `NASA_API_KEY` | No | NASA APOD API key |
| `SATQUERY_MOCK` | No | Set `true` for demo mode (no API calls) |

## Architecture

- **Frontend:** React 19 + Vite 8 + Three.js (custom 3D globe with GLSL shaders)
- **Backend:** FastAPI + Pydantic + agentic controller pipeline
- **AI:** DeepSeek (reasoning) + NVIDIA Nemotron (vision) via OpenAI SDK
- **Globe:** Custom Three.js with day/night cycle, clouds, atmosphere, universe

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/query` | Run analysis pipeline |
| POST | `/api/upload` | Upload images |
| GET | `/api/tools` | List model registry |
| POST | `/api/ai/chat` | DeepSeek chat |
| POST | `/api/ai/vision-parse` | Nemotron vision |
| GET | `/api/nasa/apod` | NASA APOD feed |
| GET | `/api/trace/{id}` | Execution trace |
| GET | `/api/report/{id}` | Download PDF report |
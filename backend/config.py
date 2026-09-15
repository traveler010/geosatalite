"""
SatQuery AI — Configuration
"""

import logging

import os
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
REPORTS_DIR = BASE_DIR / "reports"
UPLOAD_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# ─── Supported Formats ──────────────────────────────────
SUPPORTED_IMAGE_FORMATS = {".tif", ".tiff", ".geotiff", ".png", ".jpg", ".jpeg"}
GEOTIFF_FORMATS = {".tif", ".tiff", ".geotiff"}
BENCHMARK_FORMATS = {".png", ".jpg", ".jpeg"}

# ─── Model / Inference ──────────────────────────────────
# When real models are available, set these to actual checkpoint paths
MODEL_CHECKPOINT_DIR = os.getenv("SATQUERY_MODEL_DIR", str(BASE_DIR / "checkpoints"))
USE_MOCK_INFERENCE = os.getenv("SATQUERY_MOCK", "true").lower() == "true"

# ─── NASA APOD API ──────────────────────────────────────
NASA_BASE_URL = os.getenv(
    "NASA_BASE_URL", "https://science.nasa.gov/wp-json/wp/v2/apod-basic"
)
NASA_API_KEY = os.getenv("NASA_API_KEY", "")

# ─── NVIDIA AI Integration ──────────────────────────────
NVIDIA_BASE_URL = os.getenv(
    "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"
)

# Chatbot AI: DeepSeek reasoning model
NVIDIA_CHAT_API_KEY = os.getenv("NVIDIA_CHAT_API_KEY", "")
NVIDIA_CHAT_MODEL = os.getenv(
    "NVIDIA_CHAT_MODEL", "deepseek-ai/deepseek-v4-flash-0731"
)

# Visual Image Processing: Nemotron Parse 2.0
NVIDIA_VISION_API_KEY = os.getenv("NVIDIA_VISION_API_KEY", "")
NVIDIA_VISION_MODEL = os.getenv(
    "NVIDIA_VISION_MODEL", "nvidia/nemotron-parse-2.0"
)

# ─── Confidence Thresholds ──────────────────────────────
CONFIDENCE_HIGH = 0.80
CONFIDENCE_MEDIUM = 0.55
CONFIDENCE_LOW = 0.30

# ─── Upload Limits ──────────────────────────────────────
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB per file
ALLOWED_MIME_TYPES = {
    "image/tiff", "image/jpeg", "image/png",
    "image/geotiff", "application/octet-stream",
}

# ─── CORS ────────────────────────────────────────────────
DEFAULT_ORIGINS = [
    "http://localhost:5173",   # Vite dev server
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
_cors_env = os.getenv("SATQUERY_CORS_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else DEFAULT_ORIGINS


# ─── Startup Validation ─────────────────────────────────
_logger = logging.getLogger("satquery.config")

def _warn_missing_key(name: str, value: str) -> None:
    if not value:
        _logger.warning(f"⚠ {name} is not set. Related features will be unavailable.")

_warn_missing_key("NASA_API_KEY", NASA_API_KEY)
_warn_missing_key("NVIDIA_CHAT_API_KEY", NVIDIA_CHAT_API_KEY)
_warn_missing_key("NVIDIA_VISION_API_KEY", NVIDIA_VISION_API_KEY)


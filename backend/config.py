"""
SatQuery AI — Configuration
"""

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
NASA_API_KEY = os.getenv(
    "NASA_API_KEY", "mrcH27uIs4gX9tPYIeBl0GFD62p49pMxmlas7vlq4"
)

# ─── Confidence Thresholds ──────────────────────────────
CONFIDENCE_HIGH = 0.80
CONFIDENCE_MEDIUM = 0.55
CONFIDENCE_LOW = 0.30

# ─── CORS ────────────────────────────────────────────────
ALLOWED_ORIGINS = [
    "http://localhost:5173",   # Vite dev server
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

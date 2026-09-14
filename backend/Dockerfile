# ==============================================================================
# SatQuery AI — Backend Dockerfile
# Lightweight Python 3.11 container for FastAPI remote sensing assistant
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output for real-time logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    SATQUERY_MOCK=true \
    PORT=8000

WORKDIR /app

# Install curl for container health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first to leverage Docker layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy backend source code into /app/backend to preserve package namespace
COPY . /app/backend

# Ensure upload and report directories exist
RUN mkdir -p /app/backend/uploads /app/backend/reports

# Expose backend port
EXPOSE 8000

# Docker Healthcheck
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start Uvicorn with hot-reload enabled for local development
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

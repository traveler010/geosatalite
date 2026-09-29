"""
SatQuery AI — Centralized Logging Configuration

Provides unified logging setup for API, geospatial processing, satellite services,
providers, database, and agent orchestration.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

DEFAULT_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> None:
    """Initialize centralized logging handlers and formatters."""
    global _configured
    if _configured:
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
    console_handler.setFormatter(formatter)

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    # Optional file logging
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as err:
            print(f"[WARN] Failed to configure file logger at {log_file}: {err}", file=sys.stderr)

    # Tame overly verbose external loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("rasterio").setLevel(logging.WARNING)

    _configured = True
    logging.getLogger("satquery").info("Centralized logging initialized.")


def get_logger(name: str) -> logging.Logger:
    """Retrieve a namespaced SatQuery logger."""
    if not _configured:
        setup_logging()
    if not name.startswith("satquery.") and name != "satquery":
        name = f"satquery.{name}"
    return logging.getLogger(name)

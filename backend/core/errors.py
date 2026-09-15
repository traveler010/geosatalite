"""
SatQuery AI — Structured Exceptions & Error Handling

Standardized exception classes and global error handlers for clean JSON responses.
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse

from backend.core.logging import get_logger

logger = get_logger("errors")


class SatQueryException(Exception):
    """Base exception for all SatQuery domain errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class ProviderUnavailableError(SatQueryException):
    """Raised when an external or local model provider is unavailable."""

    def __init__(self, provider_name: str, reason: str = "Unavailable"):
        super().__init__(
            message=f"Provider '{provider_name}' is unavailable: {reason}",
            code="PROVIDER_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"provider": provider_name, "reason": reason},
        )


class InputCompatibilityError(SatQueryException):
    """Raised when input image count, modality, or format violates requirements."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="INPUT_COMPATIBILITY_MISMATCH",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details or {},
        )


class GeospatialProcessingError(SatQueryException):
    """Raised when GeoTIFF parsing, CRS conversion, or alignment fails."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="GEOSPATIAL_PROCESSING_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details or {},
        )


class DatabaseError(SatQueryException):
    """Raised when relational persistence operations fail."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {},
        )


async def satquery_exception_handler(request: Request, exc: SatQueryException) -> JSONResponse:
    """Global FastAPI handler for SatQuery domain exceptions."""
    logger.warning(
        f"Domain exception on {request.method} {request.url.path}: [{exc.code}] {exc.message}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global fallback handler for unexpected runtime exceptions."""
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during processing.",
                "details": {"type": type(exc).__name__},
            },
        },
    )

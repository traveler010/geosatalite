"""
SatQuery AI — Provider Abstraction Interfaces

Defines base provider classes for LLMs, Vision models, Satellite data sources, and Storage.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    LLM = "llm"
    VISION = "vision"
    SATELLITE = "satellite"
    STORAGE = "storage"


class ProviderStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    MOCK = "mock"


class ProviderMetadata(BaseModel):
    name: str
    provider_type: ProviderType
    status: ProviderStatus = ProviderStatus.OFFLINE
    version: str = "1.0.0"
    models: List[str] = Field(default_factory=list)
    description: str = ""
    is_mock: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)


class LLMResult(BaseModel):
    content: str
    reasoning: Optional[str] = None
    model: str = ""
    latency_ms: float = 0.0
    usage: Dict[str, int] = Field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None


class VisionResult(BaseModel):
    boxes: List[Dict[str, Any]] = Field(default_factory=list)
    labels: List[str] = Field(default_factory=list)
    text: Optional[str] = None
    markdown: Optional[str] = None
    model: str = ""
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


class SatelliteProduct(BaseModel):
    product_id: str
    sensor: str  # Sentinel-2, Sentinel-1, Landsat, NASA-APOD, etc.
    modality: str  # optical, sar, multispectral
    acquisition_date: str
    cloud_cover_percentage: Optional[float] = None
    bbox: List[float] = Field(default_factory=list)  # [min_lon, min_lat, max_lon, max_lat]
    preview_url: Optional[str] = None
    download_url: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class BaseProvider(ABC):
    """Abstract base class for all system providers."""

    def __init__(self, name: str, provider_type: ProviderType):
        self.name = name
        self.provider_type = provider_type
        self.status = ProviderStatus.OFFLINE

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize provider connections and resources."""
        pass

    @abstractmethod
    async def health_check(self) -> ProviderStatus:
        """Evaluate provider connectivity and status."""
        pass

    def is_available(self) -> bool:
        return self.status in (ProviderStatus.HEALTHY, ProviderStatus.MOCK)

    def get_metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            name=self.name,
            provider_type=self.provider_type,
            status=self.status,
            is_mock=self.status == ProviderStatus.MOCK,
        )


class BaseLLMProvider(BaseProvider):
    """Abstract provider for reasoning and language model synthesis."""

    def __init__(self, name: str):
        super().__init__(name, ProviderType.LLM)

    @abstractmethod
    async def generate_chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResult:
        """Generate response with optional reasoning chain-of-thought."""
        pass


class BaseVisionProvider(BaseProvider):
    """Abstract provider for visual object grounding and parsing."""

    def __init__(self, name: str):
        super().__init__(name, ProviderType.VISION)

    @abstractmethod
    async def parse_visual(
        self,
        image_path_or_url: str,
        prompt: Optional[str] = None,
        task_tokens: Optional[List[str]] = None,
    ) -> VisionResult:
        """Extract bounding boxes, labels, and structured text from imagery."""
        pass


class BaseSatelliteProvider(BaseProvider):
    """Abstract provider for satellite catalog search and imagery fetch."""

    def __init__(self, name: str):
        super().__init__(name, ProviderType.SATELLITE)

    @abstractmethod
    async def search_imagery(
        self,
        bbox: List[float],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_cloud_cover: float = 20.0,
        sensor: Optional[str] = None,
        limit: int = 10,
    ) -> List[SatelliteProduct]:
        """Search satellite catalog for matching scenes."""
        pass

    @abstractmethod
    async def fetch_preview(
        self,
        product: SatelliteProduct,
        target_path: str,
        bbox: Optional[List[float]] = None,
    ) -> str:
        """Fetch and cache AOI preview image."""
        pass


class BaseStorageProvider(BaseProvider):
    """Abstract provider for session file storage."""

    def __init__(self, name: str):
        super().__init__(name, ProviderType.STORAGE)

    @abstractmethod
    def save_file(self, relative_path: str, data: bytes) -> str:
        pass

    @abstractmethod
    def get_file(self, relative_path: str) -> Optional[bytes]:
        pass

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        pass

    @abstractmethod
    def delete(self, relative_path: str) -> bool:
        pass

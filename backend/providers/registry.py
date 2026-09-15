"""
SatQuery AI — Provider Registry & Fallback Orchestrator

Manages provider discovery, lifecycle, health monitoring, and fallback chains.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from backend.core.logging import get_logger
from backend.providers.base import (
    BaseLLMProvider,
    BaseProvider,
    BaseSatelliteProvider,
    BaseVisionProvider,
    ProviderMetadata,
    ProviderStatus,
    ProviderType,
)
from backend.providers.copernicus_provider import CopernicusProvider
from backend.providers.deepseek_provider import DeepSeekProvider
from backend.providers.local_llm_provider import LocalLLMProvider
from backend.providers.nasa_provider import NASAProvider
from backend.providers.nvidia_provider import NvidiaProvider

logger = get_logger("providers.registry")


class ProviderRegistry:
    """Singleton Registry managing provider lifecycles and fallback mechanisms."""

    _instance: Optional[ProviderRegistry] = None

    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._initialized = False

    @classmethod
    def get_instance(cls) -> ProviderRegistry:
        if cls._instance is None:
            cls._instance = ProviderRegistry()
            # Auto-register core providers
            cls._instance.register(DeepSeekProvider())
            cls._instance.register(LocalLLMProvider())
            cls._instance.register(NvidiaProvider())
            cls._instance.register(CopernicusProvider())
            cls._instance.register(NASAProvider())
        return cls._instance

    def register(self, provider: BaseProvider) -> None:
        self._providers[provider.name] = provider
        logger.info(f"Registered provider: '{provider.name}' ({provider.provider_type.value})")

    async def initialize_all(self) -> None:
        if self._initialized:
            return

        for name, provider in self._providers.items():
            try:
                await provider.initialize()
            except Exception as err:
                logger.error(f"Failed to initialize provider '{name}': {err}")

        self._initialized = True
        logger.info("ProviderRegistry initialization complete.")

    def get(self, name: str) -> Optional[BaseProvider]:
        return self._providers.get(name)

    def get_provider(self, name: str) -> Optional[BaseProvider]:
        return self._providers.get(name)

    def is_available(self, name: str) -> bool:
        p = self._providers.get(name)
        return p.is_available() if p else False

    def get_llm_provider(self, preferred: Optional[str] = None) -> BaseLLMProvider:
        """Resolve LLM provider with fallback chain: DeepSeek -> LocalLLM."""
        if preferred and preferred in self._providers:
            p = self._providers[preferred]
            if isinstance(p, BaseLLMProvider) and p.is_available():
                return p

        deepseek = self._providers.get("deepseek")
        if isinstance(deepseek, BaseLLMProvider) and deepseek.is_available():
            return deepseek

        local = self._providers.get("local_llm")
        if isinstance(local, BaseLLMProvider):
            return local

        # Absolute safety fallback
        return LocalLLMProvider()

    def get_vision_provider(self, preferred: Optional[str] = None) -> Optional[BaseVisionProvider]:
        """Resolve Vision provider."""
        if preferred and preferred in self._providers:
            p = self._providers[preferred]
            if isinstance(p, BaseVisionProvider) and p.is_available():
                return p

        nvidia = self._providers.get("nvidia_vision")
        if isinstance(nvidia, BaseVisionProvider):
            return nvidia
        return None

    def get_satellite_provider(self, preferred: Optional[str] = None) -> BaseSatelliteProvider:
        """Resolve Satellite provider: Copernicus (default) or NASA."""
        if preferred and preferred in self._providers:
            p = self._providers[preferred]
            if isinstance(p, BaseSatelliteProvider) and p.is_available():
                return p

        copernicus = self._providers.get("copernicus")
        if isinstance(copernicus, BaseSatelliteProvider):
            return copernicus

        nasa = self._providers.get("nasa")
        if isinstance(nasa, BaseSatelliteProvider):
            return nasa

        return CopernicusProvider()

    def list_providers(self) -> List[ProviderMetadata]:
        return [p.get_metadata() for p in self._providers.values()]

    async def health_check_all(self) -> Dict[str, ProviderStatus]:
        results = {}
        for name, provider in self._providers.items():
            try:
                status = await provider.health_check()
                results[name] = status
            except Exception as err:
                logger.warning(f"Health check failed for provider '{name}': {err}")
                results[name] = ProviderStatus.OFFLINE
        return results

"""
SatQuery AI — Provider Management Endpoints

Inspect provider availability, status, and health.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.providers.registry import ProviderRegistry

router = APIRouter(prefix="/api/providers", tags=["Providers"])


@router.get("")
async def list_providers():
    """List all registered providers and their current status."""
    registry = ProviderRegistry.get_instance()
    health_results = await registry.health_check_all()

    providers_info = []
    for name, provider in registry._providers.items():
        status_val = health_results.get(name)
        providers_info.append({
            "name": name,
            "type": provider.__class__.__name__,
            "status": status_val.value if status_val else "unknown",
            "is_available": registry.is_available(name),
        })

    return {
        "count": len(providers_info),
        "providers": providers_info,
    }


@router.get("/{name}/health")
async def provider_health(name: str):
    """Check health for an individual provider."""
    registry = ProviderRegistry.get_instance()
    provider = registry.get(name)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{name}' not found in registry",
        )

    health_status = await provider.health_check()
    return {
        "name": name,
        "type": provider.__class__.__name__,
        "status": health_status.value,
        "is_available": registry.is_available(name),
    }

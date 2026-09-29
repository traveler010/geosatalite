"""
SatQuery AI — NASA Satellite & Space Provider

Fetches NASA APOD and space imagery using httpx with connection pooling.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

from backend.config import NASA_BASE_URL, NASA_API_KEY, UPLOAD_DIR
from backend.core.logging import get_logger
from backend.providers.base import BaseSatelliteProvider, ProviderStatus, SatelliteProduct

logger = get_logger("providers.nasa")


class NASAProvider(BaseSatelliteProvider):
    """NASA Astronomy Picture of the Day (APOD) & space imagery provider."""

    def __init__(self):
        super().__init__("nasa")
        self.base_url = NASA_BASE_URL.rstrip("/")
        self.api_key = NASA_API_KEY
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            follow_redirects=True,
            headers={
                "User-Agent": "SatQueryAI/1.0",
                "Accept": "application/json",
            },
        )
        self.status = ProviderStatus.HEALTHY
        logger.info("NASAProvider initialized.")
        return True

    async def health_check(self) -> ProviderStatus:
        if not self._client:
            self.status = ProviderStatus.OFFLINE
            return self.status
        try:
            headers = {}
            if self.api_key:
                headers["X-API-KEY"] = self.api_key
            r = await self._client.get(f"{self.base_url}?per_page=1", headers=headers, timeout=5.0)
            self.status = ProviderStatus.HEALTHY if r.status_code < 500 else ProviderStatus.DEGRADED
        except Exception:
            self.status = ProviderStatus.DEGRADED
        return self.status

    async def search_imagery(
        self,
        bbox: List[float],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_cloud_cover: float = 20.0,
        sensor: Optional[str] = None,
        limit: int = 10,
    ) -> List[SatelliteProduct]:
        if not self._client:
            await self.initialize()

        url = f"{self.base_url}?per_page={min(limit, 20)}"
        headers = {}
        if self.api_key:
            headers["X-API-KEY"] = self.api_key

        products: List[SatelliteProduct] = []
        try:
            resp = await self._client.get(url, headers=headers)
            if resp.status_code == 200:
                items = resp.json()
                for item in items:
                    date_str = item.get("date", "")
                    title = item.get("title", {}).get("rendered", "") if isinstance(item.get("title"), dict) else item.get("title", "")
                    img_url = item.get("hdurl") or item.get("url") or ""
                    products.append(
                        SatelliteProduct(
                            product_id=f"nasa_apod_{item.get('id', uuid.uuid4().hex[:8])}",
                            sensor="NASA-APOD",
                            modality="optical",
                            acquisition_date=date_str,
                            cloud_cover_percentage=0.0,
                            bbox=bbox,
                            preview_url=img_url,
                            download_url=img_url,
                            properties={"title": title, "explanation": item.get("explanation", "")},
                        )
                    )
        except Exception as err:
            logger.warning(f"NASA search error: {err}")

        return products

    async def fetch_preview(
        self,
        product: SatelliteProduct,
        target_path: str,
        bbox: Optional[List[float]] = None,
    ) -> str:
        if not self._client:
            await self.initialize()
        url = product.preview_url or product.download_url
        if not url:
            raise ValueError("Product has no preview URL")

        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        resp = await self._client.get(url)
        resp.raise_for_status()
        with open(target, "wb") as f:
            f.write(resp.content)
        return str(target)

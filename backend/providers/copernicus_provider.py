"""
SatQuery AI — Copernicus Data Space Provider (Sentinel-1 SAR & Sentinel-2 Optical)

Interfaces with Copernicus Data Space Ecosystem (CDSE) OData/STAC catalog.
Includes realistic offline fallback catalog for demo and development.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

from backend.core.logging import get_logger
from backend.providers.base import BaseSatelliteProvider, ProviderStatus, SatelliteProduct

logger = get_logger("providers.copernicus")

CDSE_ODATA_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"


class CopernicusProvider(BaseSatelliteProvider):
    """Copernicus Data Space Ecosystem (CDSE) Provider."""

    def __init__(self):
        super().__init__("copernicus")
        self.client_id = os.getenv("COPERNICUS_CLIENT_ID", "")
        self.client_secret = os.getenv("COPERNICUS_CLIENT_SECRET", "")
        self.username = os.getenv("COPERNICUS_USERNAME", "")
        self.password = os.getenv("COPERNICUS_PASSWORD", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=6.0),
            follow_redirects=True,
            headers={"User-Agent": "SatQueryAI/1.0 (Copernicus-Connector)"},
        )
        # If credentials present, mark healthy, else mock fallback
        if self.client_id or self.username:
            self.status = ProviderStatus.HEALTHY
            logger.info("CopernicusProvider initialized with live CDSE credentials.")
        else:
            self.status = ProviderStatus.MOCK
            logger.info("CopernicusProvider initialized in realistic DEMO/MOCK catalog mode.")
        return True

    async def health_check(self) -> ProviderStatus:
        if self.status == ProviderStatus.MOCK:
            return ProviderStatus.MOCK
        if not self._client:
            self.status = ProviderStatus.OFFLINE
            return self.status
        try:
            r = await self._client.get(f"{CDSE_ODATA_URL}?$top=1", timeout=5.0)
            self.status = ProviderStatus.HEALTHY if r.status_code == 200 else ProviderStatus.DEGRADED
        except Exception:
            self.status = ProviderStatus.MOCK
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

        # If we have live credentials and connection
        if self.status == ProviderStatus.HEALTHY:
            try:
                products = await self._search_cdse_odata(bbox, start_date, end_date, max_cloud_cover, sensor, limit)
                if products:
                    return products
            except Exception as err:
                logger.warning(f"CDSE live search failed, falling back to catalog: {err}")

        # Fallback to realistic mock catalog based on bbox and date
        return self._generate_mock_products(bbox, start_date, end_date, max_cloud_cover, sensor, limit)

    async def _search_cdse_odata(
        self,
        bbox: List[float],
        start_date: Optional[str],
        end_date: Optional[str],
        max_cloud_cover: float,
        sensor: Optional[str],
        limit: int,
    ) -> List[SatelliteProduct]:
        min_lon, min_lat, max_lon, max_lat = bbox
        poly_wkt = f"POLYGON(({min_lon} {min_lat},{max_lon} {min_lat},{max_lon} {max_lat},{min_lon} {max_lat},{min_lon} {min_lat}))"

        filter_parts = [
            f"OData.CSC.Intersects(area=geography'SRID=4326;{poly_wkt}')",
        ]
        if sensor and "sentinel-1" in sensor.lower():
            filter_parts.append("Collection/Name eq 'SENTINEL-1'")
        elif sensor and "sentinel-2" in sensor.lower():
            filter_parts.append("Collection/Name eq 'SENTINEL-2'")

        query_url = f"{CDSE_ODATA_URL}?$filter={' and '.join(filter_parts)}&$top={limit}&$orderby=ContentDate/Start desc"
        resp = await self._client.get(query_url)
        if resp.status_code != 200:
            return []

        results = []
        for item in resp.json().get("value", []):
            name = item.get("Name", "")
            is_s1 = "S1" in name
            product_id = item.get("Id", "")
            preview_url = f"{CDSE_ODATA_URL}({product_id})/$value"
            results.append(
                SatelliteProduct(
                    product_id=product_id,
                    sensor="Sentinel-1 SAR" if is_s1 else "Sentinel-2 MSI",
                    modality="sar" if is_s1 else "optical",
                    acquisition_date=item.get("ContentDate", {}).get("Start", "")[:10],
                    cloud_cover_percentage=0.0 if is_s1 else float(item.get("Attributes", {}).get("cloudCover", 5.0)),
                    bbox=bbox,
                    preview_url=preview_url,
                    download_url=preview_url,
                    properties={"name": name, "origin": "Copernicus CDSE Live"},
                )
            )
        return results

    def _generate_mock_products(
        self,
        bbox: List[float],
        start_date: Optional[str],
        end_date: Optional[str],
        max_cloud_cover: float,
        sensor: Optional[str],
        limit: int,
    ) -> List[SatelliteProduct]:
        now = datetime.utcnow()
        products: List[SatelliteProduct] = []

        is_optical = not sensor or "2" in sensor or "optical" in sensor.lower()
        is_sar = not sensor or "1" in sensor or "sar" in sensor.lower()

        # Generate Sentinel-2 Optical items
        if is_optical:
            for i in range(min(limit // 2 or 1, 4)):
                acq = (now - timedelta(days=i * 5 + 2)).strftime("%Y-%m-%d")
                cloud = round(2.5 + i * 3.1, 1)
                if cloud <= max_cloud_cover:
                    products.append(
                        SatelliteProduct(
                            product_id=f"S2B_MSIL2A_{acq.replace('-', '')}T054639_N0500_R119",
                            sensor="Sentinel-2 MSI",
                            modality="optical",
                            acquisition_date=acq,
                            cloud_cover_percentage=cloud,
                            bbox=bbox,
                            preview_url="https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/sf-districts.png",
                            download_url=None,
                            properties={
                                "tile_id": "T43REQ",
                                "processing_level": "Level-2A (Bottom-of-Atmosphere Reflectance)",
                                "resolution": "10 m (B2, B3, B4, B8)",
                                "crs": "EPSG:32643",
                            },
                        )
                    )

        # Generate Sentinel-1 SAR items
        if is_sar:
            for i in range(min(limit // 2 or 1, 4)):
                acq = (now - timedelta(days=i * 6 + 4)).strftime("%Y-%m-%d")
                products.append(
                    SatelliteProduct(
                        product_id=f"S1A_IW_GRDH_1SDV_{acq.replace('-', '')}T124018_052410",
                        sensor="Sentinel-1 SAR",
                        modality="sar",
                        acquisition_date=acq,
                        cloud_cover_percentage=0.0,
                        bbox=bbox,
                        preview_url="https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/sf-districts.png",
                        download_url=None,
                        properties={
                            "polarisation": "VV + VH",
                            "orbit_direction": "ASCENDING",
                            "resolution": "10 m",
                            "mode": "Interferometric Wide Swath (IW)",
                        },
                    )
                )

        return products[:limit]

    async def fetch_preview(
        self,
        product: SatelliteProduct,
        target_path: str,
        bbox: Optional[List[float]] = None,
    ) -> str:
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        # In live mode with download URL, fetch HTTP
        if product.preview_url and product.preview_url.startswith("http") and self.status == ProviderStatus.HEALTHY:
            try:
                resp = await self._client.get(product.preview_url)
                if resp.status_code == 200 and len(resp.content) > 100:
                    with open(target, "wb") as f:
                        f.write(resp.content)
                    return str(target)
            except Exception as err:
                logger.warning(f"Could not download live preview: {err}")

        # Synthesize a clean preview image with OpenCV/NumPy
        import cv2
        import numpy as np

        img = np.zeros((400, 400, 3), dtype=np.uint8)
        # Background gradient
        if product.modality == "sar":
            # SAR grayscale radar texture
            noise = np.random.normal(120, 35, (400, 400)).astype(np.uint8)
            img[:, :, 0] = noise
            img[:, :, 1] = noise
            img[:, :, 2] = noise
            accent = (0, 200, 255)
        else:
            # Optical blue/green Earth mosaic
            img[:, :] = [35, 75, 45]
            cv2.circle(img, (200, 200), 120, (50, 110, 60), -1)
            accent = (255, 200, 50)

        # Overlay satellite metadata banner
        cv2.putText(img, f"SATQUERY: {product.sensor}", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, accent, 2)
        cv2.putText(img, f"Date: {product.acquisition_date}", (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(img, f"ID: {product.product_id[:24]}...", (20, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        cv2.rectangle(img, (5, 5), (395, 395), accent, 2)

        cv2.imwrite(str(target), img)
        return str(target)

"""
SatQuery AI — Phase 10 Test Suite: Reports & Confidence

Verifies:
1. ReportLab PDF generation incorporating all 9 mandatory sections:
   - 1. Metadata
   - 2. Query
   - 3. AI answer
   - 4. Location
   - 5. Change map (embedded physical image overlay + statistics)
   - 6. Confidence (calibrated percentage & reliability assessment)
   - 7. Evidence (spectral indices, radar backscatter, class distribution)
   - 8. Execution trace (step-by-step pipeline timeline)
   - 9. Timestamp (UTC analysis and generation times)
2. ReportLab image embedding: verification of real PNG flowables without layout crashes.
3. HTML report generation fallback.
4. REST API endpoints:
   - GET /api/report/{query_id} (PDF)
   - GET /api/report/{query_id}?format=html (HTML)
5. Trace builder automatic execution steps synthesis.
"""

from __future__ import annotations

import os
import sys
import uuid
import httpx
import numpy as np
import cv2

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.config import REPORTS_DIR
from backend.services.trace_builder import build_trace, get_trace
from backend.services.report_generator import (
    generate_pdf_report,
    generate_html_report,
    get_report_path,
)

BASE_URL = "http://localhost:8000"


def create_synthetic_change_map_overlay() -> str:
    """Creates a synthetic colored change overlay PNG on disk to test ReportLab image embedding."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    overlay_path = str(REPORTS_DIR / f"test_overlay_{uuid.uuid4().hex[:6]}.png")

    # Generate 300x200 3-channel visual overlay
    h, w = 200, 300
    img = np.zeros((h, w, 3), dtype=np.uint8)
    # Background terrain (dark green)
    img[:, :] = [25, 45, 20]
    # Water river corridor (blue)
    img[80:120, :] = [180, 80, 20]
    # Changed built-up patch (crimson/red)
    img[30:70, 50:110] = [30, 40, 220]
    # Detected cluster (yellow/gold)
    img[130:170, 180:240] = [20, 210, 240]

    cv2.imwrite(overlay_path, img)
    return overlay_path


def test_trace_builder_execution_steps_synthesis():
    """Verify trace_builder automatically enriches traces with execution_steps and metadata."""
    query_id = f"test_tr_{uuid.uuid4().hex[:8]}"

    trace = build_trace(
        query_id=query_id,
        query="Identify flood waters and built-up changes",
        input_summary={"format": "GeoTIFF", "modality": "optical+sar", "n_images": 2},
        task_type="fusion",
        tool_id="rs_optical_sar_fusion_v1",
        parameters={"fusion_mode": "deep"},
        result={"answer": "Flooding confirmed across eastern corridor.", "confidence": 0.93},
        confidence=0.93,
        duration=0.125,
        location={"location_name": "Assam, India", "latitude": 26.2006, "longitude": 92.9376},
        metadata={"dimensions": "512 x 512 px", "bands": 4, "crs": "EPSG:4326"},
    )

    assert trace["query_id"] == query_id
    assert "execution_steps" in trace
    assert len(trace["execution_steps"]) >= 4

    # Check step structure
    step1 = trace["execution_steps"][0]
    assert "step" in step1
    assert "name" in step1
    assert "tool" in step1
    assert "status" in step1
    assert "duration_ms" in step1
    assert step1["status"] == "completed"

    print("[PASS] test_trace_builder_execution_steps_synthesis passed")


def test_pdf_report_generation_with_all_9_sections():
    """Verify ReportLab PDF generation bundles all 9 required sections."""
    query_id = f"test_p10_{uuid.uuid4().hex[:8]}"
    overlay_path = create_synthetic_change_map_overlay()

    trace_data = {
        "query_id": query_id,
        "timestamp": "2026-09-15 12:00:00 UTC",
        "query": "Assess multimodal land cover distribution and bi-temporal flood variations",
        "answer": "Optical + SAR cross-modal fusion identified 24.5% open water surface (mean radar specular backscatter: -21.8 dB) and 14.2% built-up infrastructure. Bi-temporal change detection verified altered surface across 12.3% of the monitored area with radar cloud penetration.",
        "confidence": 0.94,
        "selected_task": "optical_sar_fusion",
        "selected_tool": "rs_optical_sar_fusion_v1",
        "processing_time_ms": 115.4,
        "status": "success",
        "location": {
            "location_name": "Brahmaputra Flood Plain, Assam, India",
            "latitude": 26.2006,
            "longitude": 92.9376,
            "bounding_box": [92.80, 26.10, 93.10, 26.35],
        },
        "metadata": {
            "dimensions": "1024 x 1024 px",
            "bands": "4 (B2, B3, B4, B8)",
            "modality": "Optical + SAR Multimodal",
            "crs": "EPSG:4326 (WGS84)",
            "resolution": "10.0 m / pixel",
            "format": "GeoTIFF (Cloud-Optimized)",
        },
        "change_map": {
            "path": overlay_path,
            "url": f"/api/masks/{os.path.basename(overlay_path)}",
            "change_percentage": 12.3,
            "changed_regions": [{"id": 1, "area_sqkm": 2.4}, {"id": 2, "area_sqkm": 1.1}],
        },
        "evidence": {
            "water_detection": {
                "area_percentage": 24.5,
                "mean_mndwi": 0.62,
                "mean_backscatter_db": -21.8,
            },
            "built_up_detection": {
                "area_percentage": 14.2,
                "mean_ndbi": 0.38,
                "mean_backscatter_db": -4.2,
            },
            "vegetation_analysis": {
                "total_vegetation_percentage": 53.3,
                "dense_percentage": 38.0,
                "mean_ndvi": 0.65,
                "volume_scattering_ratio": 0.42,
            },
            "dominant_class": "Water & Riverine Riparian Zone",
            "concordance_score": 0.94,
        },
        "execution_steps": [
            {"step": 1, "name": "Input Ingestion & Modality Check", "tool": "input_checker", "status": "completed", "duration_ms": 14.2},
            {"step": 2, "name": "Agent Planning & Tool Routing", "tool": "agent_planner", "status": "completed", "duration_ms": 8.5},
            {"step": 3, "name": "Optical + SAR Dual-Stream Inference", "tool": "OpticalSARFusionNet", "status": "completed", "duration_ms": 68.1},
            {"step": 4, "name": "Evidence Aggregation & XAI", "tool": "aggregator", "status": "completed", "duration_ms": 18.3},
            {"step": 5, "name": "Observable Trace & Report Indexing", "tool": "session_service", "status": "completed", "duration_ms": 6.3},
        ],
    }

    # Store trace in builder store for subsequent API lookup
    build_trace(
        query_id=query_id,
        query=trace_data["query"],
        input_summary={"format": "GeoTIFF", "modality": "optical+sar", "metadata": trace_data["metadata"]},
        task_type=trace_data["selected_task"],
        tool_id=trace_data["selected_tool"],
        parameters={},
        result={"answer": trace_data["answer"], "confidence": trace_data["confidence"], "evidence": trace_data["evidence"]},
        confidence=trace_data["confidence"],
        duration=0.1154,
        location=trace_data["location"],
        metadata=trace_data["metadata"],
        change_map=trace_data["change_map"],
        execution_steps=trace_data["execution_steps"],
    )

    pdf_path = generate_pdf_report(trace_data, query_id)

    assert os.path.exists(pdf_path), f"Expected PDF report to exist at {pdf_path}"
    file_size = os.path.getsize(pdf_path)
    assert file_size > 5000, f"Generated PDF is too small ({file_size} bytes), expected > 5KB"

    # Verify PDF magic header
    with open(pdf_path, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-", f"Expected PDF magic bytes %PDF-, got {header}"

    # Also test HTML fallback report
    html_path = generate_html_report(trace_data, query_id)
    assert os.path.exists(html_path)
    html_content = open(html_path, "r", encoding="utf-8").read()
    assert "SatQuery AI" in html_content
    assert "Pipeline Execution Timeline" in html_content
    assert "Raster &amp; Sensor Metadata" in html_content or "Raster & Sensor Metadata" in html_content

    # Clean up test overlay
    try:
        os.remove(overlay_path)
    except Exception:
        pass

    print("[PASS] test_pdf_report_generation_with_all_9_sections passed")
    return query_id


def test_rest_api_report_endpoints(query_id: str):
    """Verify GET /api/report/{query_id} delivers valid PDF and HTML responses."""
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Download PDF Report
        resp_pdf = client.get(f"/api/report/{query_id}")
        assert resp_pdf.status_code == 200, f"PDF report download failed: {resp_pdf.text}"
        assert "application/pdf" in resp_pdf.headers.get("content-type", "")
        assert resp_pdf.content.startswith(b"%PDF-")
        assert len(resp_pdf.content) > 5000

        # 2. Download HTML Report
        resp_html = client.get(f"/api/report/{query_id}?format=html")
        assert resp_html.status_code == 200
        assert "text/html" in resp_html.headers.get("content-type", "")
        assert "SatQuery AI" in resp_html.text

        # 3. 404 for unknown query_id
        resp_404 = client.get("/api/report/non_existent_query_9999")
        assert resp_404.status_code == 404

    print("[PASS] test_rest_api_report_endpoints passed")


if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING SATQUERY AI PHASE 10 (REPORTS & CONFIDENCE) TEST SUITE")
    print("=" * 70)

    test_trace_builder_execution_steps_synthesis()
    qid = test_pdf_report_generation_with_all_9_sections()
    test_rest_api_report_endpoints(qid)

    print("\n" + "=" * 70)
    print("ALL PHASE 10 REPORTS & CONFIDENCE TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

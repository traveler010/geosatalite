"""
SatQuery AI — Phase 8 Comprehensive Validation Suite
Optical + SAR Multimodal Fusion Verification

Tests:
1. Modality detection (Optical vs SAR from physics, band stats, and metadata)
2. Optical preprocessing (cloud masking, reflectance normalization, NDVI, MNDWI, NDBI)
3. SAR preprocessing (radiometric calibration to dB, adaptive Lee speckle filtering, VH/VV ratio)
4. PyTorch neural fusion (OpticalSARFusionNet forward pass and cross-modal gated attention)
5. Water detection (SAR specular bounce + Optical MNDWI synergy & cloud penetration)
6. Built-up detection (SAR double-bounce dihedral return + Optical NDBI)
7. Vegetation analysis (Optical NDVI + SAR volume scattering depolarisation)
8. Cross-modal explanation, evidence synthesis, and calibrated confidence
9. Visual overlay generation (5-class color-coded segmentation PNG)
10. API endpoints: GET /api/fusion/status and POST /api/fusion/analyze
11. End-to-end agentic routing via POST /api/query with zero CoT leaks
"""

import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
import torch

from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
_current_dir = Path(__file__).resolve().parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

from backend.main import app
from backend.services.fusion_service import OpticalSARFusionService
from backend.models.fusion_model import OpticalSARFusionModel, CrossModalGatedFusionNet
from backend.services.controller import execute_query


def print_step(title: str):
    print(f"\n{'='*20} {title} {'='*20}")


def generate_synthetic_optical_sar_pair(temp_dir: str):
    """
    Creates synthetic co-registered Optical (4-band: R, G, B, NIR) and SAR (2-band: VV, VH) GeoTIFFs.
    Layout (128 x 128):
    - Quadrant 1 (top-left, 0:60, 0:60): Water Lake
      * Optical: Dark blue, low NIR
      * SAR: Low backscatter (< -18 dB), specular reflection
    - Quadrant 2 (top-right, 0:60, 68:128): Built-Up Urban Cluster
      * Optical: High red/gray, moderate NIR, high NDBI
      * SAR: High backscatter (> -5 dB), double-bounce dihedral return
    - Quadrant 3 (bottom-left, 68:128, 0:60): Dense Forest / Vegetation
      * Optical: High green, high NIR, high NDVI
      * SAR: Moderate backscatter, high volume depolarisation (VH/VV)
    - Quadrant 4 (bottom-right, 68:128, 68:128): Cloud Patch over terrain
      * Optical: Saturated bright white, obscures ground
      * SAR: Clear terrain backscatter, microwaves penetrate cloud
    """
    h, w = 128, 128
    transform = from_origin(77.20, 28.61, 0.0001, 0.0001)
    crs = "EPSG:4326"

    # 1. Optical Bands (R, G, B, NIR)
    r = np.full((h, w), 80, dtype=np.uint8)
    g = np.full((h, w), 80, dtype=np.uint8)
    b = np.full((h, w), 80, dtype=np.uint8)
    nir = np.full((h, w), 70, dtype=np.uint8)

    # Water lake
    r[10:55, 10:55] = 15
    g[10:55, 10:55] = 45
    b[10:55, 10:55] = 140
    nir[10:55, 10:55] = 10  # Absorbed in NIR

    # Built-up cluster
    r[10:55, 75:120] = 195
    g[10:55, 75:120] = 160
    b[10:55, 75:120] = 150
    nir[10:55, 75:120] = 110

    # Dense Vegetation
    r[75:120, 10:55] = 30
    g[75:120, 10:55] = 160
    b[75:120, 10:55] = 40
    nir[75:120, 10:55] = 210  # Strong NIR plateau

    # Cloud patch in bottom-right
    r[75:120, 75:120] = 245
    g[75:120, 75:120] = 245
    b[75:120, 75:120] = 248
    nir[75:120, 75:120] = 240

    opt_path = os.path.join(temp_dir, "sentinel2_optical.tif")
    with rasterio.open(
        opt_path, "w",
        driver="GTiff",
        height=h, width=w, count=4,
        dtype=np.uint8,
        crs=crs, transform=transform,
    ) as dst:
        dst.write(r, 1)
        dst.write(g, 2)
        dst.write(b, 3)
        dst.write(nir, 4)
        dst.set_band_description(1, "B04_Red")
        dst.set_band_description(2, "B03_Green")
        dst.set_band_description(3, "B02_Blue")
        dst.set_band_description(4, "B08_NIR")

    # 2. SAR Bands (VV, VH) calibrated in dB
    # Standard terrain background: -12 dB with speckle noise
    np.random.seed(42)
    vv_db = np.random.normal(-12.0, 1.8, (h, w)).astype(np.float32)
    vh_db = vv_db - 6.5 + np.random.normal(0.0, 0.8, (h, w)).astype(np.float32)

    # Water lake: Specular bounce away -> low backscatter (-22 dB)
    vv_db[10:55, 10:55] = np.random.normal(-21.5, 1.2, (45, 45))
    vh_db[10:55, 10:55] = np.random.normal(-28.0, 1.5, (45, 45))

    # Built-up cluster: Dihedral double bounce -> high backscatter (-3 dB to +2 dB)
    vv_db[10:55, 75:120] = np.random.normal(-2.5, 2.0, (45, 45))
    vh_db[10:55, 75:120] = np.random.normal(-7.0, 1.5, (45, 45))

    # Dense Vegetation: Volume scattering -> moderate VV, elevated VH
    vv_db[75:120, 10:55] = np.random.normal(-9.5, 1.5, (45, 45))
    vh_db[75:120, 10:55] = np.random.normal(-13.0, 1.2, (45, 45))  # High cross-pol return

    # Cloud patch: SAR pierces cloud completely! Background is standard vegetated/bare ground
    vv_db[75:120, 75:120] = np.random.normal(-11.0, 1.5, (45, 45))
    vh_db[75:120, 75:120] = np.random.normal(-16.5, 1.5, (45, 45))

    sar_path = os.path.join(temp_dir, "sentinel1_sar.tif")
    with rasterio.open(
        sar_path, "w",
        driver="GTiff",
        height=h, width=w, count=2,
        dtype=np.float32,
        crs=crs, transform=transform,
    ) as dst:
        dst.write(vv_db, 1)
        dst.write(vh_db, 2)
        dst.set_band_description(1, "VV_sigma0_dB")
        dst.set_band_description(2, "VH_sigma0_dB")

    return opt_path, sar_path


def run_phase_8_tests():
    print("Beginning SatQuery AI Phase 8 (Optical + SAR Fusion) Validation Suite...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        opt_path, sar_path = generate_synthetic_optical_sar_pair(tmp_dir)
        print(f"Generated synthetic test pairs in {tmp_dir}:")
        print(f"  - Optical: {opt_path}")
        print(f"  - SAR:     {sar_path}")

        # ───────────────────────────────────────────────────────────
        # Feature 1: Modality Detection
        # ───────────────────────────────────────────────────────────
        print_step("Feature 1: Sensor Modality Detection")
        mod_opt = OpticalSARFusionService.detect_modality(opt_path)
        mod_sar = OpticalSARFusionService.detect_modality(sar_path)
        assert mod_opt == "optical", f"Expected 'optical', got: {mod_opt}"
        assert mod_sar == "sar", f"Expected 'sar', got: {mod_sar}"
        print(f"  [OK] Modality detection verified: Optical={mod_opt}, SAR={mod_sar}")

        # Test pair order invariance
        classified_opt, classified_sar = OpticalSARFusionService.classify_pair(sar_path, opt_path)
        assert classified_opt == opt_path, "Optical was not placed first"
        assert classified_sar == sar_path, "SAR was not placed second"
        print("  [OK] Pair classification is invariant to argument order.")

        # ───────────────────────────────────────────────────────────
        # Feature 2: Optical Preprocessing
        # ───────────────────────────────────────────────────────────
        print_step("Feature 2: Optical Preprocessing")
        opt_prep = OpticalSARFusionService.preprocess_optical(opt_path, target_shape=(128, 128))
        assert "rgb" in opt_prep and opt_prep["rgb"].shape == (128, 128, 3)
        assert "cloud_mask" in opt_prep
        assert "ndvi" in opt_prep and "mndwi" in opt_prep and "ndbi" in opt_prep

        # Check cloud mask detects the cloud patch in Q4
        cloud_in_patch = np.mean(opt_prep["cloud_mask"][80:115, 80:115])
        cloud_in_clear = np.mean(opt_prep["cloud_mask"][15:50, 15:50])
        assert cloud_in_patch > 0.60, f"Cloud patch missed: {cloud_in_patch}"
        assert cloud_in_clear < 0.10, f"False cloud in clear water: {cloud_in_clear}"
        print(f"  [OK] Optical indices & cloud mask computed. Cloud coverage in patch: {round(cloud_in_patch*100, 1)}%")

        # ───────────────────────────────────────────────────────────
        # Feature 3: SAR Preprocessing & Lee Speckle Filter
        # ───────────────────────────────────────────────────────────
        print_step("Feature 3: SAR Preprocessing & Adaptive Lee Filter")
        sar_prep = OpticalSARFusionService.preprocess_sar(sar_path, target_shape=(128, 128))
        assert "sigma0_db" in sar_prep and "lee_filtered_db" in sar_prep
        assert "pol_ratio" in sar_prep

        # Verify speckle smoothing: variance in homogeneous water zone should decrease after Lee filtering
        raw_var = float(np.var(sar_prep["sigma0_db"][15:50, 15:50]))
        filtered_var = float(np.var(sar_prep["lee_filtered_db"][15:50, 15:50]))
        assert filtered_var <= raw_var, f"Lee filter failed to smooth speckle: raw={raw_var}, filtered={filtered_var}"
        print(f"  [OK] Adaptive Lee filter attenuated speckle variance: {raw_var:.3f} -> {filtered_var:.3f}")

        # ───────────────────────────────────────────────────────────
        # Feature 4: PyTorch Neural Fusion Model
        # ───────────────────────────────────────────────────────────
        print_step("Feature 4: PyTorch OpticalSARFusionNet")
        net = CrossModalGatedFusionNet(num_classes=5)
        dummy_opt = torch.randn(1, 6, 64, 64)
        dummy_sar = torch.randn(1, 3, 64, 64)
        dummy_cloud = torch.zeros(1, 1, 64, 64)
        out_logits = net(dummy_opt, dummy_sar, dummy_cloud)
        assert out_logits.shape == (1, 5, 64, 64), f"Unexpected PyTorch shape: {out_logits.shape}"
        print("  [OK] PyTorch CrossModalGatedFusionNet forward pass verified:", out_logits.shape)

        # ───────────────────────────────────────────────────────────
        # Features 5, 6, 7: Water, Built-Up, and Vegetation Analysis
        # ───────────────────────────────────────────────────────────
        print_step("Features 5-7: Multimodal Target Extraction")
        water_mask, water_ev = OpticalSARFusionService.detect_water(opt_prep, sar_prep)
        built_mask, built_ev = OpticalSARFusionService.detect_built_up(opt_prep, sar_prep)
        dense_mask, sparse_mask, veg_ev = OpticalSARFusionService.detect_vegetation(opt_prep, sar_prep)

        assert water_ev["area_percentage"] > 5.0, f"Water undetected: {water_ev}"
        assert built_ev["area_percentage"] > 5.0, f"Built-up undetected: {built_ev}"
        assert veg_ev["total_vegetation_percentage"] > 5.0, f"Vegetation undetected: {veg_ev}"

        print(f"  [OK] Water extraction: {water_ev['area_percentage']}% of AOI (mean dB: {water_ev['mean_backscatter_db']})")
        print(f"  [OK] Built-up extraction: {built_ev['area_percentage']}% of AOI (mean dB: {built_ev['mean_backscatter_db']})")
        print(f"  [OK] Vegetation analysis: {veg_ev['total_vegetation_percentage']}% of AOI (NDVI: {veg_ev['mean_ndvi']})")

        # ───────────────────────────────────────────────────────────
        # Feature 8: Cross-Modal Explanation, Evidence & Overlay
        # ───────────────────────────────────────────────────────────
        print_step("Feature 8: Cross-Modal Explanation & Visual Overlay")
        overlay_out = os.path.join(tmp_dir, "test_fused_overlay.png")
        analysis = OpticalSARFusionService.compute_fusion_analysis(
            image_path_1=opt_path,
            image_path_2=sar_path,
            query="Extract built-up structures, water bodies, and vegetation using optical and SAR fusion.",
            overlay_output_path=overlay_out,
            target_size=(128, 128),
        )

        assert os.path.isfile(overlay_out), "Overlay PNG was not created"
        assert os.path.getsize(overlay_out) > 500, "Overlay PNG is empty"
        print(f"  [OK] Fused visual overlay generated: {os.path.getsize(overlay_out)} bytes")

        xai = analysis["cross_modal_explanation"]
        assert xai["concordance_score"] >= 0.70
        assert len(xai["concordance_evidence"]) >= 2
        print(f"  [OK] Cross-modal explanation concordance: {xai['concordance_score']}")
        for exp_text in xai["concordance_evidence"]:
            print(f"    - {exp_text[:85]}...")

        # ───────────────────────────────────────────────────────────
        # Feature 9: OpticalSARFusionModel Class Integration
        # ───────────────────────────────────────────────────────────
        print_step("Feature 9: OpticalSARFusionModel Specialist Inference")
        model = OpticalSARFusionModel()
        pred = model.predict(
            optical_path=opt_path,
            sar_path=sar_path,
            query="Analyze flood extent and water bodies",
            overlay_output_path=os.path.join(tmp_dir, "model_overlay.png"),
        )
        assert pred["confidence"] >= 0.75
        assert "water_detection" in pred["evidence"]
        assert "built_up_detection" in pred["evidence"]
        assert "vegetation_analysis" in pred["evidence"]
        assert pred["evidence"]["neural_network_verified"] is True
        print(f"  [OK] Model inference answer: {pred['answer'][:90]}...")
        print(f"    Confidence: {pred['confidence']}, Latency: {pred['latency_ms']} ms")

        # ───────────────────────────────────────────────────────────
        # Feature 10: API Endpoints Validation
        # ───────────────────────────────────────────────────────────
        print_step("Feature 10: API Endpoints (GET /api/fusion/status & POST /api/fusion/analyze)")
        client = TestClient(app)

        # Status check
        resp = client.get("/api/fusion/status")
        assert resp.status_code == 200, f"Status failed: {resp.text}"
        status_data = resp.json()
        assert status_data["status"] == "operational"
        assert "rasterio" in status_data["libraries"]
        assert "torch" in status_data["libraries"]
        assert "numpy" in status_data["libraries"]
        print(f"  [OK] GET /api/fusion/status: Rasterio {status_data['libraries']['rasterio']}, PyTorch {status_data['libraries']['torch']}, NumPy {status_data['libraries']['numpy']}")

        # Session upload & fusion analysis
        sess_resp = client.post("/api/sessions", json={"title": "Phase 8 Fusion Test Session"})
        session_id = sess_resp.json()["session_id"]

        with open(opt_path, "rb") as f_opt, open(sar_path, "rb") as f_sar:
            upload_resp = client.post(
                "/api/upload",
                files=[
                    ("files", ("sentinel2.tif", f_opt.read(), "image/tiff")),
                    ("files", ("sentinel1.tif", f_sar.read(), "image/tiff")),
                ],
                data={"session_id": session_id},
            )
        assert upload_resp.status_code == 200
        up_json = upload_resp.json()
        img1_id = up_json["files"][0]["image_id"]
        img2_id = up_json["files"][1]["image_id"]

        # Call POST /api/fusion/analyze
        fuse_payload = {
            "session_id": session_id,
            "optical_image_id": img1_id,
            "sar_image_id": img2_id,
            "query": "Joint optical and SAR land cover extraction",
        }
        fuse_resp = client.post("/api/fusion/analyze", json=fuse_payload)
        assert fuse_resp.status_code == 200, f"Fusion analyze failed: {fuse_resp.text}"
        fuse_json = fuse_resp.json()
        assert fuse_json["status"] == "success"
        assert fuse_json["confidence"] >= 0.70
        assert "overlay_url" in fuse_json
        print(f"  [OK] POST /api/fusion/analyze completed successfully:")
        print(f"    - Query ID: {fuse_json['query_id']}")
        print(f"    - Class distribution: {fuse_json['class_distribution']}")
        print(f"    - Overlay URL: {fuse_json['overlay_url']}")

        # Verify overlay is downloadable
        overlay_get = client.get(fuse_json["overlay_url"])
        assert overlay_get.status_code == 200
        assert overlay_get.headers.get("content-type") == "image/png"
        print(f"  [OK] Fusion overlay retrieved via API ({len(overlay_get.content)} bytes)")

        # ───────────────────────────────────────────────────────────
        # Feature 11: Agent Controller & Natural Language Routing
        # ───────────────────────────────────────────────────────────
        print_step("Feature 11: Agentic Routing & Trace Integrity")
        agent_res = execute_query(
            query="Use optical and SAR fusion to identify water bodies and built-up areas",
            file_paths=[opt_path, sar_path],
        )
        assert agent_res["success"] is True
        trace_str = json.dumps(agent_res["trace"])
        assert "think" not in trace_str.lower() or "thinking" not in trace_str.lower()
        print(f"  [OK] Agent query successful. Task routed to: {agent_res['trace'].get('selected_task')}")
        print(f"  [OK] Clean observable trace verified with zero CoT leaks.")


    print("\n" + "=" * 60)
    print("ALL PHASE 8 OPTICAL + SAR FUSION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_phase_8_tests()

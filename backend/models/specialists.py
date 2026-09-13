"""
SatQuery AI — Specialist Model Wrappers

Each class wraps a specialist model for one mandatory task:
  - VQASpecialist          (RSVQA / VRSBench)
  - GroundingSpecialist    (VRSBench referring expressions)
  - CaptioningSpecialist   (VRSBench captions)
  - ChangeVQASpecialist    (CDVQA)
  - FusionSpecialist       (BigEarthNet optical+SAR)

Currently using **mock inference** that returns realistic structured outputs.
To plug in real models, replace the `predict()` method in each class.
"""

from __future__ import annotations

import random
import hashlib
from typing import Any


def _deterministic_seed(query: str, image_hash: str = "") -> int:
    """Produce a deterministic seed from query + image so demo outputs are stable."""
    h = hashlib.md5(f"{query}:{image_hash}".encode()).hexdigest()
    return int(h[:8], 16)


# ─── VQA Specialist ─────────────────────────────────────

class VQASpecialist:
    """Single-image Visual Question Answering."""

    tool_id = "rs_vqa_v1"

    # Demo answer banks per question type
    _ANSWER_BANK = {
        "presence": [
            ("Yes, {target} is visible in the image.", 0.92),
            ("No, {target} is not detected in this image.", 0.87),
            ("Yes, multiple instances of {target} are present.", 0.94),
        ],
        "count": [
            ("There are approximately 3 {target} visible in this scene.", 0.85),
            ("I count 7 {target} in the image.", 0.81),
            ("There is 1 {target} in the analyzed region.", 0.90),
        ],
        "comparison": [
            ("The urban area is larger than the vegetation region.", 0.78),
            ("Water coverage exceeds the built-up area in this scene.", 0.82),
        ],
        "color": [
            ("The predominant color of the region is green, indicating dense vegetation.", 0.88),
            ("The area appears brownish-grey, consistent with bare soil or arid terrain.", 0.84),
        ],
        "position": [
            ("The {target} is located in the northeast quadrant of the image.", 0.86),
            ("The {target} is centrally positioned within the scene.", 0.89),
        ],
        "scene": [
            ("This is an urban residential area with mixed commercial zones.", 0.91),
            ("The scene depicts an agricultural landscape with irrigated fields.", 0.88),
            ("This appears to be a coastal industrial zone with port infrastructure.", 0.85),
        ],
        "reasoning": [
            ("Based on the spectral signatures and spatial patterns, this area is undergoing rapid urbanization with new construction visible in the southern portion.", 0.79),
            ("The vegetation index suggests healthy crop growth in the irrigated fields, while the adjacent dryland shows signs of water stress.", 0.76),
        ],
    }

    def predict(self, image_path: str, question: str, question_type: str = "scene", **kwargs) -> dict:
        """Run VQA inference. Currently returns mock output."""
        seed = _deterministic_seed(question, image_path)
        rng = random.Random(seed)

        # Extract target from question
        target = self._extract_target(question)

        # Pick an answer from the bank
        bank = self._ANSWER_BANK.get(question_type, self._ANSWER_BANK["scene"])
        template, base_confidence = rng.choice(bank)
        answer = template.format(target=target)

        # Add slight confidence jitter
        confidence = round(min(0.99, max(0.55, base_confidence + rng.uniform(-0.05, 0.05))), 3)

        return {
            "answer": answer,
            "confidence": confidence,
            "question_type": question_type,
            "model_used": "rs_vqa_v1 (mock)",
        }

    @staticmethod
    def _extract_target(question: str) -> str:
        """Pull a likely target noun from the question."""
        keywords = ["aircraft", "building", "water", "vehicle", "ship", "bridge",
                     "road", "forest", "field", "stadium", "airport", "river",
                     "storage tank", "solar panel", "runway", "harbor"]
        q_lower = question.lower()
        for kw in keywords:
            if kw in q_lower:
                return kw
        return "the target object"


# ─── Grounding Specialist ───────────────────────────────

class GroundingSpecialist:
    """Text-guided region localization producing bounding boxes."""

    tool_id = "rs_grounding_v1"

    def predict(self, image_path: str, description: str, image_width: int = 512, image_height: int = 512, **kwargs) -> dict:
        """Run grounding inference. Currently returns mock bounding boxes."""
        seed = _deterministic_seed(description, image_path)
        rng = random.Random(seed)

        num_boxes = rng.randint(1, 4)
        boxes = []
        for i in range(num_boxes):
            x1 = rng.randint(20, image_width // 2)
            y1 = rng.randint(20, image_height // 2)
            w = rng.randint(40, min(200, image_width - x1))
            h = rng.randint(40, min(200, image_height - y1))
            conf = round(rng.uniform(0.72, 0.97), 3)
            boxes.append({
                "bbox": [x1, y1, x1 + w, y1 + h],
                "label": f"{description.split()[0:3]}",
                "confidence": conf,
                "detection_id": i + 1,
            })

        avg_conf = round(sum(b["confidence"] for b in boxes) / len(boxes), 3)

        return {
            "bounding_boxes": boxes,
            "num_detections": len(boxes),
            "confidence": avg_conf,
            "model_used": "rs_grounding_v1 (mock)",
        }


# ─── Captioning Specialist ──────────────────────────────

class CaptioningSpecialist:
    """Generates natural-language descriptions of RS images."""

    tool_id = "rs_caption_v1"

    _CAPTIONS = [
        "An aerial view of an urban area with dense residential buildings, intersected by a network of roads. Several green patches indicate parks or vegetation corridors. A water body is visible in the southwest corner.",
        "A rural agricultural landscape showing a mosaic of cultivated fields in various stages of growth. Irrigation canals run north-south through the scene. A small settlement cluster is visible in the eastern portion.",
        "A coastal region featuring a sandy shoreline with breaking waves. Behind the beach, mixed vegetation transitions into built-up commercial infrastructure. A harbor with docked vessels is visible to the north.",
        "An industrial zone with large warehouse structures, storage tanks, and connecting road infrastructure. Railway lines run along the southern boundary. Adjacent residential areas are separated by a green buffer zone.",
        "A mountainous terrain with exposed rock faces and scattered vegetation. A river valley cuts through the center, with a small town along its banks. Terraced agriculture is visible on the hillslopes.",
    ]

    def predict(self, image_path: str, detail_level: str = "detailed", **kwargs) -> dict:
        """Run captioning inference. Currently returns mock output."""
        seed = _deterministic_seed(image_path)
        rng = random.Random(seed)

        caption = rng.choice(self._CAPTIONS)
        confidence = round(rng.uniform(0.78, 0.95), 3)

        return {
            "caption": caption,
            "confidence": confidence,
            "detail_level": detail_level,
            "model_used": "rs_caption_v1 (mock)",
        }


# ─── Change VQA Specialist ──────────────────────────────

class ChangeVQASpecialist:
    """Bi-temporal change detection and VQA."""

    tool_id = "cdvqa_change_v1"

    _CHANGE_ANSWERS = {
        "binary": [
            ("Yes, significant changes are detected between the two timestamps.", 0.91),
            ("No, the area remains largely unchanged.", 0.88),
        ],
        "trend": [
            ("Built-up area has increased, concentrated in the northeast quadrant.", 0.87),
            ("Vegetation coverage has decreased by approximately 15% between the two dates.", 0.83),
            ("Water body extent has expanded, likely due to seasonal flooding.", 0.85),
        ],
        "class_transition": [
            ("Agricultural land has been converted to residential built-up area.", 0.84),
            ("Bare soil regions have transitioned to vegetated land, indicating reforestation.", 0.80),
            ("Water body has receded, exposing bare soil along the shoreline.", 0.82),
        ],
        "count_change": [
            ("The number of buildings has increased from approximately 12 to 28.", 0.79),
            ("Vehicle count decreased from 45 to 18 between timestamps.", 0.77),
        ],
    }

    def predict(self, image_path_t1: str, image_path_t2: str, question: str, question_type: str = "trend", **kwargs) -> dict:
        """Run change VQA inference. Currently returns mock output."""
        seed = _deterministic_seed(question, f"{image_path_t1}:{image_path_t2}")
        rng = random.Random(seed)

        bank = self._CHANGE_ANSWERS.get(question_type, self._CHANGE_ANSWERS["trend"])
        answer, base_conf = rng.choice(bank)
        confidence = round(min(0.99, max(0.55, base_conf + rng.uniform(-0.05, 0.05))), 3)

        # Mock change map reference
        change_map = f"changemap_{seed % 10000:04d}.png"

        return {
            "answer": answer,
            "confidence": confidence,
            "question_type": question_type,
            "change_map_ref": change_map,
            "model_used": "cdvqa_change_v1 (mock)",
        }


# ─── Optical–SAR Fusion Specialist ──────────────────────

class FusionSpecialist:
    """Joint optical + SAR analysis for land cover classification."""

    tool_id = "optical_sar_fusion_v1"

    _FUSION_RESULTS = [
        {
            "answer": "The co-registered optical and SAR analysis reveals three distinct land cover zones: built-up urban infrastructure (34% of the scene, high SAR backscatter + urban spectral signature), water bodies (18%, low SAR backscatter + water absorption features), and mixed vegetation (48%, moderate SAR texture + high NDVI).",
            "classes": {"built_up": 34.2, "water": 18.1, "vegetation": 42.5, "bare_soil": 5.2},
        },
        {
            "answer": "Fusion of optical RGB and SAR imagery identifies extensive water coverage (52% of scene) with built-up regions along the eastern shoreline (21%). The SAR component confirms the water boundary more precisely than optical alone due to specular reflection characteristics.",
            "classes": {"built_up": 21.0, "water": 52.3, "vegetation": 19.8, "bare_soil": 6.9},
        },
        {
            "answer": "Cross-modal analysis shows dominant vegetation cover (61%) with scattered built-up clusters (15%). SAR texture analysis reveals subsurface moisture patterns not visible in the optical data, suggesting recent precipitation in the southwestern quadrant.",
            "classes": {"built_up": 15.4, "water": 8.2, "vegetation": 61.0, "bare_soil": 15.4},
        },
    ]

    def predict(self, optical_path: str, sar_path: str, target_classes: list[str] | None = None, **kwargs) -> dict:
        """Run fusion inference. Currently returns mock output."""
        seed = _deterministic_seed(f"{optical_path}:{sar_path}")
        rng = random.Random(seed)

        result = rng.choice(self._FUSION_RESULTS)
        confidence = round(rng.uniform(0.75, 0.92), 3)

        return {
            "answer": result["answer"],
            "class_distribution": result["classes"],
            "confidence": confidence,
            "fusion_mode": "early",
            "model_used": "optical_sar_fusion_v1 (mock)",
        }


# ─── Factory ────────────────────────────────────────────

_SPECIALIST_MAP = {
    "vqa": VQASpecialist,
    "grounding": GroundingSpecialist,
    "captioning": CaptioningSpecialist,
    "change_vqa": ChangeVQASpecialist,
    "fusion": FusionSpecialist,
}


def get_specialist(task_type: str):
    """Return an instantiated specialist for the given task type."""
    cls = _SPECIALIST_MAP.get(task_type)
    if cls is None:
        raise ValueError(f"No specialist registered for task type: {task_type}")
    return cls()

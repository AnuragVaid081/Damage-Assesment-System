"""
yolo_service.py
===============
YOLO segmentation inference service for the Damage Assessment System.

Responsibilities
----------------
- Load the trained YOLO11n-seg model ONCE at import time (singleton).
- Run inference on every supplied image path.
- Return structured, normalised detections with stable IDs.
- Convert absolute bounding-box pixel coords to percentage coords required
  by the existing frontend contract.
- Keep image-to-detection association intact for downstream services.

YOLO class mapping (trained model)
------------------------------------
0: Lost Parts
1: Torn
2: Dented
3: Paint Scratches
4: Puncture
5: Broken Glass
6: Broken Lamp

This module must NOT attempt to identify vehicle parts (e.g. "front door").
That is exclusively Gemini's responsibility.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLASS_NAMES: dict[int, str] = {
    0: "Lost Parts",
    1: "Torn",
    2: "Dented",
    3: "Paint Scratches",
    4: "Puncture",
    5: "Broken Glass",
    6: "Broken Lamp",
}

# Resolve model path — prefer env var, fall back to known relative location.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # …/Damage-Assesment-System/

_DEFAULT_MODEL_PATH = (
    _PROJECT_ROOT
    / "runs"
    / "segment"
    / "ai"
    / "runs"
    / "yolo11n-baseline-8"
    / "weights"
    / "best.pt"
)

YOLO_MODEL_PATH: Path = Path(
    os.environ.get("YOLO_MODEL_PATH", str(_DEFAULT_MODEL_PATH))
)

YOLO_CONF_THRESHOLD: float = float(os.environ.get("YOLO_CONF_THRESHOLD", "0.25"))

# ---------------------------------------------------------------------------
# Lazy singleton — the model is loaded the first time it is needed.
# ---------------------------------------------------------------------------

_model: Any | None = None
_model_load_error: Exception | None = None


def _get_model() -> Any:
    """Return the cached YOLO model, loading it on first call."""
    global _model, _model_load_error

    if _model is not None:
        return _model

    if _model_load_error is not None:
        raise _model_load_error

    try:
        from ultralytics import YOLO  # type: ignore

        if not YOLO_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"YOLO model weights not found at: {YOLO_MODEL_PATH}\n"
                "Set YOLO_MODEL_PATH in your .env file to the correct path."
            )

        logger.info("Loading YOLO model from %s", YOLO_MODEL_PATH)
        _model = YOLO(str(YOLO_MODEL_PATH))
        logger.info(
            "YOLO model loaded successfully. Confidence threshold: %.2f",
            YOLO_CONF_THRESHOLD,
        )
        return _model

    except Exception as exc:
        _model_load_error = exc
        logger.error("Failed to load YOLO model: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Detection schema helpers
# ---------------------------------------------------------------------------


def _bbox_to_pct(
    x1: float, y1: float, x2: float, y2: float, img_w: int, img_h: int
) -> dict[str, str]:
    """
    Convert absolute pixel bounding-box corners to the percentage-based format
    expected by the existing frontend anomaly contract.

    Returns: {"top": "32.50%", "left": "41.20%", "width": "18.30%", "height": "22.10%"}
    """
    top = (y1 / img_h) * 100
    left = (x1 / img_w) * 100
    width = ((x2 - x1) / img_w) * 100
    height = ((y2 - y1) / img_h) * 100

    # Clamp to [0, 100] to handle any floating-point edge cases.
    top = max(0.0, min(100.0, top))
    left = max(0.0, min(100.0, left))
    width = max(0.0, min(100.0 - left, width))
    height = max(0.0, min(100.0 - top, height))

    return {
        "top": f"{top:.2f}%",
        "left": f"{left:.2f}%",
        "width": f"{width:.2f}%",
        "height": f"{height:.2f}%",
    }


def _extract_polygon(masks: Any, idx: int) -> list[list[float]] | None:
    """
    Safely extract the segmentation polygon for a given detection index.

    Returns a list of [x, y] pairs (absolute pixels), or None if unavailable.
    """
    try:
        if masks is None:
            return None
        xy = masks.xy  # list of numpy arrays, one per detection
        if idx >= len(xy):
            return None
        pts = xy[idx]
        if pts is None or len(pts) == 0:
            return None
        return pts.tolist()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_on_images(image_paths: list[str]) -> list[dict]:
    """
    Run YOLO inference on every supplied image path.

    Parameters
    ----------
    image_paths : list[str]
        Absolute or resolvable paths to the vehicle images to analyse.

    Returns
    -------
    list[dict]  — one entry per image, even if it produced zero detections:

    [
      {
        "image_path":     "/abs/path/to/img.jpg",
        "image_filename": "img.jpg",
        "img_width":      1280,
        "img_height":     720,
        "detections": [
          {
            "detection_id":  "img_00_det_00",   # stable cross-service key
            "class_id":       2,
            "class_name":    "Dented",
            "confidence":     0.87,
            "bbox_abs":      [x1, y1, x2, y2],  # pixel coords
            "bbox_pct":      {                   # percentage coords for frontend
              "top":    "32.50%",
              "left":   "41.20%",
              "width":  "18.30%",
              "height": "22.10%"
            },
            "polygon":       [[x, y], ...]       # segmentation points or None
          },
          ...
        ]
      },
      ...
    ]
    """
    if not image_paths:
        logger.warning("run_on_images called with an empty image list.")
        return []

    model = _get_model()
    results_per_image: list[dict] = []

    for img_idx, img_path in enumerate(image_paths):
        img_path_str = str(img_path)
        img_filename = Path(img_path_str).name
        image_record: dict = {
            "image_path": img_path_str,
            "image_filename": img_filename,
            "img_width": None,
            "img_height": None,
            "detections": [],
        }

        try:
            results = model.predict(
                source=img_path_str,
                imgsz=640,
                conf=YOLO_CONF_THRESHOLD,
                verbose=False,
            )

            # model.predict() returns a list; take the first (and only) result.
            result = results[0]

            img_h, img_w = result.orig_shape[:2]
            image_record["img_width"] = img_w
            image_record["img_height"] = img_h

            if result.boxes is None or len(result.boxes) == 0:
                logger.debug("No detections in %s", img_filename)
                results_per_image.append(image_record)
                continue

            boxes = result.boxes
            n_det = len(boxes)
            logger.debug("Image %s: %d detection(s)", img_filename, n_det)

            for det_idx in range(n_det):
                # Stable detection ID used by assessment_service to resolve
                # Gemini's source_detection_ids back to spatial evidence.
                detection_id = f"img_{img_idx:02d}_det_{det_idx:02d}"

                # Bounding box (xyxy, absolute pixels)
                xyxy = boxes.xyxy[det_idx].cpu().numpy()
                x1 = float(xyxy[0])
                y1 = float(xyxy[1])
                x2 = float(xyxy[2])
                y2 = float(xyxy[3])

                # Class and confidence
                class_id = int(boxes.cls[det_idx].cpu().numpy())
                confidence = float(boxes.conf[det_idx].cpu().numpy())
                class_name = CLASS_NAMES.get(class_id, f"Unknown({class_id})")

                # Percentage bbox for the frontend — generated ONLY from YOLO
                bbox_pct = _bbox_to_pct(x1, y1, x2, y2, img_w, img_h)

                # Segmentation polygon (may be None)
                polygon = _extract_polygon(result.masks, det_idx)

                image_record["detections"].append(
                    {
                        "detection_id": detection_id,
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": round(confidence, 4),
                        "bbox_abs": [
                            round(x1, 1),
                            round(y1, 1),
                            round(x2, 1),
                            round(y2, 1),
                        ],
                        "bbox_pct": bbox_pct,
                        "polygon": polygon,
                    }
                )

        except FileNotFoundError:
            logger.warning("Image not found, skipping: %s", img_path_str)
        except Exception as exc:
            logger.error(
                "YOLO inference failed for image %s: %s",
                img_filename,
                exc,
                exc_info=True,
            )

        results_per_image.append(image_record)

    return results_per_image


def build_detection_index(yolo_results: list[dict]) -> dict[str, dict]:
    """
    Build a flat index from detection_id -> detection dict for O(1) lookup
    in assessment_service when resolving Gemini's source_detection_ids.

    Parameters
    ----------
    yolo_results : list[dict]
        Output of run_on_images().

    Returns
    -------
    dict[str, dict]  e.g. {"img_00_det_00": {...detection...}, ...}
    """
    index: dict[str, dict] = {}
    for image_record in yolo_results:
        for det in image_record["detections"]:
            index[det["detection_id"]] = det
    return index

"""
assessment_service.py
=====================
Pipeline orchestrator for the Damage Assessment System.

Responsibilities
----------------
1. Accept a list of saved image paths + vehicle metadata.
2. Call yolo_service to get per-image detections with stable detection IDs.
3. Build a flat detection index (detection_id -> detection dict).
4. Call gemini_service with all images + all YOLO detections (one call).
5. Resolve Gemini's source_detection_ids back to concrete YOLO bboxes.
6. Select the primary display image using a deterministic priority algorithm.
7. Convert the consolidated results into the EXISTING frontend anomaly schema.
8. Return a fully-populated assessment dict ready for storage and rendering.

Frontend anomaly schema (preserved exactly — do not change):
{
    "part": "...",
    "confidence": 94,                 # int 0-100
    "damage_type": "...",
    "severity": "High | Medium | Low | None",
    "severity_bg": "...",             # hex colour
    "severity_color": "...",          # hex colour
    "action": "...",
    "color": "...",                   # bbox border / pin colour
    "bbox": {                         # None if no spatial evidence on primary image
        "top": "32.50%",
        "left": "41.20%",
        "width": "18.30%",
        "height": "22.10%"
    }
}

Extended backend fields stored in the assessment dict for future multi-image UI:
- "all_images"           : full list of YOLO image records (path, filename, detections)
- "yolo_detections"      : alias of all_images
- "primary_image_path"   : selected primary display image path
- "all_anomalies"        : anomalies with source_images and source_detection_ids
- "gemini_raw"           : the validated Gemini response dict
- "overall_severity"     : "Low | Moderate | High" from Gemini
- "recommendations"      : list of Gemini recommendation strings
"""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from services import yolo_service, gemini_service  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Severity -> UI colour mapping (matches existing frontend sample data exactly)
# ---------------------------------------------------------------------------

_SEVERITY_STYLES: dict[str, dict[str, str]] = {
    "High": {
        "severity_bg": "#ffdad6",
        "severity_color": "#93000a",
        "color": "#ba1a1a",
    },
    "Medium": {
        "severity_bg": "#ffede6",
        "severity_color": "#bc4800",
        "color": "#bc4800",
    },
    "Low": {
        "severity_bg": "#dbe1ff",
        "severity_color": "#003ea8",
        "color": "#004ac6",
    },
    "None": {
        "severity_bg": "",
        "severity_color": "",
        "color": "#22c55e",
    },
}

# Severity ordering for comparison (higher = worse)
_SEVERITY_RANK: dict[str, int] = {"None": 0, "Low": 1, "Medium": 2, "High": 3}

# Map Gemini's internal terms to frontend severity values
_GEMINI_SEVERITY_MAP: dict[str, str] = {
    "High": "High",
    "Moderate": "Medium",
    "Medium": "Medium",
    "Low": "Low",
}


# ---------------------------------------------------------------------------
# Helper: resolve detection_id -> source image filename
# ---------------------------------------------------------------------------


def _det_image_filename(
    detection_id: str,
    yolo_results: list[dict],
) -> str | None:
    """Resolve a detection_id to its source image filename."""
    for img_record in yolo_results:
        for det in img_record["detections"]:
            if det["detection_id"] == detection_id:
                return img_record["image_filename"]
    return None


# ---------------------------------------------------------------------------
# Primary image selection
# ---------------------------------------------------------------------------


def _first_valid_image(image_paths: list[str]) -> str:
    """Return the first image path that exists on disk."""
    for p in image_paths:
        if Path(p).exists():
            return p
    return image_paths[0] if image_paths else ""


def _select_primary_image(
    gemini_damages: list[dict],
    detection_index: dict[str, dict],
    yolo_results: list[dict],
    image_paths: list[str],
) -> str:
    """
    Select the primary display image using a deterministic priority algorithm:

    Priority 1 — Image containing the highest-severity consolidated damage.
    Priority 2 — Tie-break: image with the most mapped YOLO detections.
    Priority 3 — Tie-break: image with the highest average detection confidence.
    Priority 4 — No detections: first valid uploaded image.

    Only bboxes from the primary image are rendered in the main results view.
    All other image/detection relationships are preserved in the backend for
    future multi-image UI support.
    """
    # img_filename -> {"severity_rank", "detection_count", "total_confidence"}
    img_stats: dict[str, dict] = {}

    for dmg in gemini_damages:
        severity_str = dmg.get("severity", "Low")
        frontend_sev = _GEMINI_SEVERITY_MAP.get(severity_str, "Low")
        sev_rank = _SEVERITY_RANK.get(frontend_sev, 1)

        for det_id in dmg.get("source_detection_ids", []):
            det = detection_index.get(det_id)
            if det is None:
                continue

            img_filename = _det_image_filename(det_id, yolo_results)
            if img_filename is None:
                continue

            if img_filename not in img_stats:
                img_stats[img_filename] = {
                    "severity_rank": 0,
                    "detection_count": 0,
                    "total_confidence": 0.0,
                }

            stats = img_stats[img_filename]
            stats["severity_rank"] = max(stats["severity_rank"], sev_rank)
            stats["detection_count"] += 1
            stats["total_confidence"] += det.get("confidence", 0.0)

    if not img_stats:
        # No mapped detections — fall back to first valid uploaded image
        return _first_valid_image(image_paths)

    def sort_key(item: tuple) -> tuple:
        fname, s = item
        avg_conf = (
            s["total_confidence"] / s["detection_count"]
            if s["detection_count"]
            else 0
        )
        return (s["severity_rank"], s["detection_count"], avg_conf)

    best_filename = max(img_stats.items(), key=sort_key)[0]

    # Resolve filename -> full absolute path
    for img_path in image_paths:
        if Path(img_path).name == best_filename:
            return img_path

    return _first_valid_image(image_paths)


# ---------------------------------------------------------------------------
# Frontend anomaly construction
# ---------------------------------------------------------------------------


def _build_anomalies_for_frontend(
    gemini_damages: list[dict],
    detection_index: dict[str, dict],
    yolo_results: list[dict],
    primary_image_path: str,
) -> list[dict]:
    """
    Convert consolidated Gemini damages into the frontend anomaly schema.

    Key rules
    ---------
    - bbox ALWAYS comes from YOLO, never from Gemini.
    - Only bboxes whose source image matches primary_image_path are rendered.
    - If the best YOLO detection for a damage belongs to a different image,
      bbox is set to None (correct; do not show cross-image overlays).
    - Source image association and detection IDs are preserved in each anomaly
      for future multi-image UI extension.
    """
    primary_filename = Path(primary_image_path).name if primary_image_path else ""
    anomalies: list[dict] = []

    for dmg in gemini_damages:
        severity_str = dmg.get("severity", "Low")
        frontend_severity = _GEMINI_SEVERITY_MAP.get(severity_str, "Low")
        styles = _SEVERITY_STYLES.get(frontend_severity, _SEVERITY_STYLES["Low"])

        det_ids = dmg.get("source_detection_ids", [])

        # Resolve YOLO detections — split into primary-image and others
        primary_dets: list[dict] = []
        all_dets: list[dict] = []
        for det_id in det_ids:
            det = detection_index.get(det_id)
            if det is None:
                logger.debug("Unknown detection_id from Gemini: %s", det_id)
                continue
            all_dets.append(det)
            img_fname = _det_image_filename(det_id, yolo_results)
            if img_fname == primary_filename:
                primary_dets.append(det)

        # Best detection = highest confidence from primary image;
        # fall back to highest confidence across all images.
        best_det = max(primary_dets, key=lambda d: d["confidence"], default=None)
        if best_det is None:
            best_det = max(all_dets, key=lambda d: d["confidence"], default=None)

        # Bbox: ONLY from a detection whose source image == primary image.
        # Never display a bbox originating from another image on the primary image.
        bbox: dict | None = None
        if best_det is not None:
            source_img = _det_image_filename(best_det["detection_id"], yolo_results)
            if source_img == primary_filename:
                bbox = best_det["bbox_pct"]

        # Confidence: prefer YOLO's measured value; fallback to Gemini's estimate.
        if best_det is not None:
            confidence = round(best_det["confidence"] * 100)
        else:
            confidence = dmg.get("confidence", 50)

        anomaly: dict = {
            # --- Existing frontend contract fields (unchanged) ---
            "part": dmg.get("part", "Unknown"),
            "confidence": confidence,
            "damage_type": dmg.get("damage_type", ""),
            "severity": frontend_severity,
            "severity_bg": styles["severity_bg"],
            "severity_color": styles["severity_color"],
            "action": dmg.get("action", "Inspect"),
            "color": styles["color"],
            "bbox": bbox,
            # --- Extended fields for future multi-image UI ---
            "description": dmg.get("description", ""),
            "source_detection_ids": det_ids,
            "source_images": sorted(
                {
                    fn
                    for d in det_ids
                    if (fn := _det_image_filename(d, yolo_results)) is not None
                }
            ),
        }
        anomalies.append(anomaly)

    return anomalies


# ---------------------------------------------------------------------------
# Carousel image list builder
# ---------------------------------------------------------------------------


def _build_carousel_images(
    yolo_results: list[dict],
    anomalies: list[dict],
    primary_image_path: str,
) -> list[dict]:
    """
    Build the sorted image list for the results-page carousel.

    Order
    -----
    1. Primary image first (preserves existing primary-selection logic).
    2. Remaining images sorted by descending polygon count
       (detections that have a non-None segmentation polygon).

    Each entry carries everything the JS renderer needs:
    {
        "image_path":     "/abs/path/to/img.jpg",   # converted to URL by app.py
        "image_filename": "img.jpg",
        "polygon_count":  3,
        "bboxes": [
            {
                "top":          "32.50%",
                "left":         "41.20%",
                "width":        "18.30%",
                "height":       "22.10%",
                "color":        "#ba1a1a",
                "anomaly_index": 1,      # 1-based; matches anomaly card number
                "part":          "Front Bumper"
            }
        ]
    }

    Only bboxes that belong to this image are included in its entry — the JS
    must never render a bbox from a different image on the current image.
    """
    primary_filename = Path(primary_image_path).name if primary_image_path else ""

    # ------------------------------------------------------------------
    # Build per-image metadata from YOLO results
    # ------------------------------------------------------------------
    # image_filename -> image record
    image_records: dict[str, dict] = {}
    # image_filename -> number of detections with a polygon
    polygon_counts: dict[str, int] = {}

    for img_record in yolo_results:
        fname = img_record["image_filename"]
        image_records[fname] = img_record
        polygon_counts[fname] = sum(
            1
            for det in img_record["detections"]
            if det.get("polygon") is not None
        )

    # ------------------------------------------------------------------
    # Build per-image bbox lists from the frontend anomalies
    # ------------------------------------------------------------------
    # image_filename -> list of bbox dicts for that image
    image_bboxes: dict[str, list[dict]] = {fname: [] for fname in image_records}

    for anomaly_idx, anomaly in enumerate(anomalies, start=1):
        for det_id in anomaly.get("source_detection_ids", []):
            # Locate the detection in yolo_results
            for img_record in yolo_results:
                for det in img_record["detections"]:
                    if det["detection_id"] == det_id and det.get("bbox_pct"):
                        fname = img_record["image_filename"]
                        if fname in image_bboxes:
                            image_bboxes[fname].append(
                                {
                                    **det["bbox_pct"],
                                    "color": anomaly.get("color", "#004ac6"),
                                    "anomaly_index": anomaly_idx,
                                    "part": anomaly.get("part", ""),
                                }
                            )

    # ------------------------------------------------------------------
    # Sort: primary image first; remaining by descending polygon count
    # ------------------------------------------------------------------
    other_fnames = [
        f for f in image_records if f != primary_filename
    ]
    other_fnames.sort(key=lambda f: polygon_counts.get(f, 0), reverse=True)

    ordered_fnames: list[str] = []
    if primary_filename in image_records:
        ordered_fnames.append(primary_filename)
    ordered_fnames.extend(other_fnames)

    carousel: list[dict] = []
    for fname in ordered_fnames:
        img_record = image_records[fname]
        carousel.append(
            {
                "image_path": img_record["image_path"],
                "image_filename": fname,
                "polygon_count": polygon_counts.get(fname, 0),
                "bboxes": image_bboxes.get(fname, []),
            }
        )

    return carousel


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_assessment(
    image_paths: list[str],
    vehicle_meta: dict,
) -> dict:
    """
    Run the complete AI damage assessment pipeline for a set of vehicle images.

    Parameters
    ----------
    image_paths : list[str]
        Absolute paths to all saved vehicle images for this assessment.
    vehicle_meta : dict
        Form fields: {"make": ..., "model": ..., "year": ..., "vin": ...}

    Returns
    -------
    dict with the following structure:
    {
        # Consumed by existing frontend templates
        "summary":            str,
        "anomalies":          list[dict],   # frontend anomaly schema
        "overall_severity":   "Low | Moderate | High",
        "status":             "Completed" | "Review Required",

        # Extended fields preserved for future multi-image results UI
        "primary_image_path": str,
        "all_images":         list[dict],   # full YOLO results per image
        "yolo_detections":    list[dict],   # alias of all_images
        "gemini_raw":         dict,
        "recommendations":    list[str],
        "_fallback":          bool,
    }
    """
    logger.info(
        "Starting assessment: %d image(s), vehicle: %s %s %s",
        len(image_paths),
        vehicle_meta.get("year", ""),
        vehicle_meta.get("make", ""),
        vehicle_meta.get("model", ""),
    )

    # ------------------------------------------------------------------
    # Step 1 — YOLO inference across ALL images
    # ------------------------------------------------------------------
    yolo_results = yolo_service.run_on_images(image_paths)
    detection_index = yolo_service.build_detection_index(yolo_results)

    total_detections = sum(len(r["detections"]) for r in yolo_results)
    logger.info(
        "YOLO: %d total detection(s) across %d image(s).",
        total_detections,
        len(yolo_results),
    )

    # ------------------------------------------------------------------
    # Step 2 — Gemini multimodal reasoning (ALL images + ALL detections)
    # ------------------------------------------------------------------
    gemini_result = gemini_service.analyze_vehicle(
        image_paths=image_paths,
        yolo_detections=yolo_results,
        vehicle_meta=vehicle_meta,
    )

    # ------------------------------------------------------------------
    # Step 3 — Primary image selection (deterministic priority)
    # ------------------------------------------------------------------
    primary_image_path = _select_primary_image(
        gemini_damages=gemini_result.get("damages", []),
        detection_index=detection_index,
        yolo_results=yolo_results,
        image_paths=image_paths,
    )
    logger.info(
        "Primary display image selected: %s", Path(primary_image_path).name
    )

    # ------------------------------------------------------------------
    # Step 4 — Convert Gemini damages -> frontend anomaly schema
    #           BBoxes resolved from YOLO only; primary-image isolation enforced
    # ------------------------------------------------------------------
    anomalies = _build_anomalies_for_frontend(
        gemini_damages=gemini_result.get("damages", []),
        detection_index=detection_index,
        yolo_results=yolo_results,
        primary_image_path=primary_image_path,
    )

    # ------------------------------------------------------------------
    # Step 5 — Build carousel image list for the results page
    #           Primary first; remaining sorted by descending polygon count
    # ------------------------------------------------------------------
    carousel_images = _build_carousel_images(
        yolo_results=yolo_results,
        anomalies=anomalies,
        primary_image_path=primary_image_path,
    )

    # ------------------------------------------------------------------
    # Step 6 — Determine overall status
    # ------------------------------------------------------------------
    is_fallback = gemini_result.get("_fallback", False)
    status = "Review Required" if is_fallback else "Completed"

    logger.info(
        "Assessment complete: %d anomaly(ies), status: %s, fallback: %s",
        len(anomalies),
        status,
        is_fallback,
    )

    return {
        # Frontend template fields
        "summary": gemini_result.get("summary", "Assessment complete."),
        "anomalies": anomalies,
        "overall_severity": gemini_result.get("overall_severity", "Low"),
        "status": status,
        # Extended / future multi-image UI fields
        "primary_image_path": primary_image_path,
        "all_images": yolo_results,
        "yolo_detections": yolo_results,
        "gemini_raw": gemini_result,
        "recommendations": gemini_result.get("recommendations", []),
        "carousel_images": carousel_images,   # sorted list for results-page carousel
        "_fallback": is_fallback,
    }

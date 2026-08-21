"""
gemini_service.py
=================
Gemini multimodal reasoning service for the Damage Assessment System.

Responsibilities
----------------
- Configure the Google GenAI client (google-genai SDK).
- Accept ALL uploaded vehicle images plus ALL YOLO detections in ONE call.
- Perform a single multimodal Gemini request covering the entire vehicle.
- Request structured JSON output and validate the schema.
- Return the validated Gemini assessment dict, or a YOLO-only fallback on error.

What Gemini MUST do
--------------------
- Analyse the vehicle across all submitted images holistically.
- Consolidate duplicate observations of the same physical damage.
- Identify the likely affected vehicle part/area from visual context.
- Assess visible damage severity.
- Describe each consolidated damage.
- Recommend an appropriate inspection/repair action.
- Produce ONE combined vehicle-level summary.
- Reference YOLO detection_ids for each consolidated damage so the
  assessment_service can resolve spatial evidence (bbox, polygon).

What Gemini MUST NOT do
------------------------
- Generate or modify bounding-box coordinates.
- Estimate repair costs.
- Invent damage not visible in the images.
- Claim knowledge of internal/mechanical damage from exterior images.
- Treat YOLO detections as infallible ground truth.
- Produce separate per-image reports.
- Duplicate the same damage because it appears in multiple images.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini model configuration
# ---------------------------------------------------------------------------

GEMINI_MODEL = "gemini-3.6-flash"

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert vehicle damage assessment AI assistant used by professional \
insurance adjusters. You will be given:
1. One or more photographs of a single vehicle, showing different angles.
2. A JSON list of YOLO-detected damage regions across those photos, including \
   their detection IDs, damage type, confidence, and bounding-box location.

Your task is to produce ONE consolidated vehicle damage assessment report in \
strict JSON format.

Rules:
- Analyse ALL images together as a single vehicle — do NOT produce per-image reports.
- CONSOLIDATE overlapping or duplicate detections of the same physical damage \
  into a single damage entry, referencing all relevant YOLO detection IDs.
- Identify the likely vehicle part or area (e.g. "Front Bumper", "Driver Side Door") \
  from the visual context. YOLO detections confirm damage type and location but \
  cannot name vehicle parts — you must interpret these visually.
- Assess severity as exactly one of: "High", "Medium", or "Low".
- Recommend a practical repair/inspection action (e.g. "Replace panel", \
  "Repaint and buff", "Recommend structural inspection").
- Do NOT generate or modify bounding-box coordinates. Spatial data comes from YOLO alone.
- Do NOT estimate repair costs.
- Do NOT invent damage that is not visible.
- Do NOT claim knowledge of hidden structural/mechanical damage from exterior images.
- Be explicit that this is an AI-assisted visual assessment; recommend professional \
  physical inspection where uncertainty exists.
- Overall severity should reflect the most severe individual damage.

Respond ONLY with a valid JSON object matching EXACTLY this schema — no markdown, \
no prose, no code fences:

{
  "overall_severity": "Low | Moderate | High",
  "summary": "<one paragraph vehicle-level narrative>",
  "damages": [
    {
      "part": "<vehicle part or area>",
      "damage_type": "<damage category>",
      "severity": "High | Medium | Low",
      "description": "<concise description of this damage>",
      "action": "<recommended repair or inspection action>",
      "confidence": <integer 0-100>,
      "source_detection_ids": ["<yolo_detection_id>", ...]
    }
  ],
  "recommendations": [
    "<actionable recommendation string>"
  ]
}

If no damage is detected, return damages as an empty list and set \
overall_severity to "Low".
"""

# ---------------------------------------------------------------------------
# Expected schema keys for validation
# ---------------------------------------------------------------------------

_REQUIRED_TOP_KEYS = {"overall_severity", "summary", "damages", "recommendations"}
_VALID_OVERALL_SEVERITY = {"Low", "Moderate", "High"}
_VALID_SEVERITY = {"High", "Medium", "Low"}
_REQUIRED_DAMAGE_KEYS = {
    "part",
    "damage_type",
    "severity",
    "description",
    "action",
    "confidence",
    "source_detection_ids",
}


# ---------------------------------------------------------------------------
# Client initialisation
# ---------------------------------------------------------------------------


def _build_client() -> Any:
    """
    Initialise and return the Google GenAI client.
    Raises RuntimeError if GEMINI_API_KEY is missing.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Add it to your .env file: GEMINI_API_KEY=your_key_here"
        )
    try:
        from google import genai  # type: ignore
        from google.genai import types  # noqa: F401

        client = genai.Client(api_key=api_key)
        return client
    except ImportError as exc:
        raise ImportError(
            "google-genai is not installed. Run: pip install google-genai"
        ) from exc


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def _validate_gemini_response(data: Any) -> dict:
    """
    Validate and normalise the parsed Gemini JSON response.
    Raises ValueError with a descriptive message on schema violations.
    """
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object, got {type(data).__name__}")

    missing = _REQUIRED_TOP_KEYS - data.keys()
    if missing:
        raise ValueError(f"Gemini response missing required keys: {missing}")

    # Normalise overall_severity
    sev = str(data.get("overall_severity", "")).strip().capitalize()
    if sev not in _VALID_OVERALL_SEVERITY:
        logger.warning(
            "Unexpected overall_severity '%s', defaulting to 'Moderate'", sev
        )
        sev = "Moderate"
    data["overall_severity"] = sev

    # Validate damages list
    if not isinstance(data["damages"], list):
        raise ValueError("'damages' must be a JSON array")

    for i, dmg in enumerate(data["damages"]):
        if not isinstance(dmg, dict):
            raise ValueError(f"damages[{i}] is not a JSON object")

        missing_dmg = _REQUIRED_DAMAGE_KEYS - dmg.keys()
        if missing_dmg:
            raise ValueError(
                f"damages[{i}] missing required keys: {missing_dmg}"
            )

        # Normalise severity
        dmg_sev = str(dmg.get("severity", "")).strip().capitalize()
        if dmg_sev not in _VALID_SEVERITY:
            logger.warning(
                "damages[%d] unexpected severity '%s', defaulting to 'Low'",
                i,
                dmg_sev,
            )
            dmg_sev = "Low"
        dmg["severity"] = dmg_sev

        # Normalise confidence to int 0-100
        try:
            dmg["confidence"] = max(0, min(100, int(dmg["confidence"])))
        except (TypeError, ValueError):
            dmg["confidence"] = 50

        # Ensure source_detection_ids is a list
        if not isinstance(dmg.get("source_detection_ids"), list):
            dmg["source_detection_ids"] = []

    # Validate recommendations
    if not isinstance(data["recommendations"], list):
        data["recommendations"] = [str(data["recommendations"])]

    return data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_vehicle(
    image_paths: list[str],
    yolo_detections: list[dict],
    vehicle_meta: dict,
) -> dict:
    """
    Send all vehicle images + YOLO detections to Gemini for holistic analysis.

    Parameters
    ----------
    image_paths : list[str]
        Absolute paths to the saved vehicle images.
    yolo_detections : list[dict]
        Output of yolo_service.run_on_images() — one entry per image.
    vehicle_meta : dict
        Keys: make, model, year, vin (from the form submission).

    Returns
    -------
    dict — validated Gemini assessment, or a YOLO-only fallback on error.
    """
    try:
        return _call_gemini(image_paths, yolo_detections, vehicle_meta)
    except Exception as exc:
        logger.error(
            "Gemini analysis failed (%s). Falling back to YOLO-only assessment.",
            exc,
            exc_info=True,
        )
        return _yolo_fallback(yolo_detections, vehicle_meta, error=str(exc))


def _call_gemini(
    image_paths: list[str],
    yolo_detections: list[dict],
    vehicle_meta: dict,
) -> dict:
    """Internal: perform the actual Gemini API call."""
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore

    client = _build_client()

    # ------------------------------------------------------------------
    # Build the YOLO context text block.
    # We pass bbox_pct as text so Gemini has spatial context, but we
    # explicitly forbid it from copying or modifying these coordinates.
    # ------------------------------------------------------------------
    yolo_context_rows = []
    for img_record in yolo_detections:
        img_name = img_record["image_filename"]
        for det in img_record["detections"]:
            yolo_context_rows.append(
                {
                    "detection_id": det["detection_id"],
                    "image": img_name,
                    "damage_type": det["class_name"],
                    "confidence": det["confidence"],
                    "image_region": det["bbox_pct"],
                }
            )

    yolo_context_text = (
        "YOLO Damage Detections (do NOT copy or modify these coordinates):\n"
        + json.dumps(yolo_context_rows, indent=2)
    )

    vehicle_text = (
        f"Vehicle: {vehicle_meta.get('year', 'Unknown')} "
        f"{vehicle_meta.get('make', 'Unknown')} "
        f"{vehicle_meta.get('model', 'Unknown')} "
        f"(VIN: {vehicle_meta.get('vin', 'N/A')})"
    )

    # ------------------------------------------------------------------
    # Assemble multimodal content: [image, image, ..., text_block]
    # ALL images are sent together in one request.
    # ------------------------------------------------------------------
    content_parts: list[Any] = []

    for img_path in image_paths:
        try:
            img_path_obj = Path(img_path)
            if not img_path_obj.exists():
                logger.warning("Image not found for Gemini: %s", img_path)
                continue

            suffix = img_path_obj.suffix.lower()
            mime_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
                ".gif": "image/gif",
            }
            mime_type = mime_map.get(suffix, "image/jpeg")

            with open(img_path_obj, "rb") as fh:
                image_bytes = fh.read()

            content_parts.append(
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            )

        except Exception as exc:
            logger.warning(
                "Skipping image %s for Gemini due to error: %s", img_path, exc
            )

    if not content_parts:
        raise ValueError("No readable images available to send to Gemini.")

    # Text context block appended after all images
    content_parts.append(
        types.Part.from_text(text=f"{vehicle_text}\n\n{yolo_context_text}")
    )

    logger.info(
        "Sending %d image(s) + %d YOLO detection(s) to Gemini (%s).",
        len(content_parts) - 1,
        len(yolo_context_rows),
        GEMINI_MODEL,
    )

    # ------------------------------------------------------------------
    # Single multimodal API call
    # ------------------------------------------------------------------
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=content_parts,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            temperature=0.1,
            max_output_tokens=4096,
        ),
    )

    raw_text = response.text.strip()
    logger.debug(
        "Gemini raw response (%d chars): %.200s...", len(raw_text), raw_text
    )

    # Strip markdown code fences if Gemini wrapped them
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        raw_text = "\n".join(lines).strip()

    parsed = json.loads(raw_text)
    validated = _validate_gemini_response(parsed)

    logger.info(
        "Gemini assessment complete: %d damage(s), overall severity: %s",
        len(validated["damages"]),
        validated["overall_severity"],
    )
    return validated


# ---------------------------------------------------------------------------
# YOLO-only fallback (used when Gemini is unavailable)
# ---------------------------------------------------------------------------


def _yolo_fallback(
    yolo_detections: list[dict],
    vehicle_meta: dict,
    error: str = "",
) -> dict:
    """
    Build a best-effort assessment from YOLO detections alone when Gemini
    is unavailable. Never invents data; is honest about its limitations.
    """
    all_detections: list[dict] = []
    for img_record in yolo_detections:
        for det in img_record["detections"]:
            all_detections.append(
                {**det, "image_filename": img_record["image_filename"]}
            )

    if not all_detections:
        return {
            "overall_severity": "Low",
            "summary": (
                "No significant damage was detected in the submitted images. "
                "AI-assisted reasoning was unavailable; a professional physical "
                "inspection is recommended to confirm this result."
            ),
            "damages": [],
            "recommendations": [
                "Professional physical inspection recommended.",
                "AI reasoning service was unavailable during this assessment.",
            ],
            "_fallback": True,
            "_fallback_reason": error,
        }

    _class_severity: dict[str, str] = {
        "Lost Parts": "High",
        "Torn": "High",
        "Broken Glass": "High",
        "Puncture": "High",
        "Dented": "Medium",
        "Broken Lamp": "Medium",
        "Paint Scratches": "Low",
    }

    damages = []
    for det in all_detections:
        sev = _class_severity.get(det["class_name"], "Low")
        damages.append(
            {
                "part": f"Vehicle area ({det['image_filename']})",
                "damage_type": det["class_name"],
                "severity": sev,
                "description": (
                    f"{det['class_name']} detected with "
                    f"{det['confidence'] * 100:.0f}% confidence. "
                    "Vehicle part identification requires AI reasoning service."
                ),
                "action": "Professional inspection required to assess repair scope.",
                "confidence": round(det["confidence"] * 100),
                "source_detection_ids": [det["detection_id"]],
            }
        )

    severities = [d["severity"] for d in damages]
    if "High" in severities:
        overall = "High"
    elif "Medium" in severities:
        overall = "Moderate"
    else:
        overall = "Low"

    return {
        "overall_severity": overall,
        "summary": (
            f"YOLO detection-only assessment (AI reasoning unavailable). "
            f"{len(damages)} damage region(s) detected across the submitted "
            f"images. Vehicle part identification and damage consolidation "
            f"require the Gemini AI reasoning service. "
            f"Professional physical inspection is strongly recommended."
        ),
        "damages": damages,
        "recommendations": [
            "Professional physical inspection is strongly recommended.",
            "AI reasoning service was unavailable; results may include duplicates.",
            "Resubmit when the AI reasoning service is restored for a full assessment.",
        ],
        "_fallback": True,
        "_fallback_reason": error,
    }

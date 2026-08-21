"""
Quick validation script for the AI pipeline.
Run from project root: .venv\Scripts\python verify_pipeline.py
"""
import sys, os, json, logging
from pathlib import Path

# Resolve project root and backend dir regardless of CWD
_PROJECT_ROOT = Path(__file__).resolve().parent
_BACKEND_DIR = _PROJECT_ROOT / "backend"

# Add backend to sys.path so `services.*` imports resolve
sys.path.insert(0, str(_BACKEND_DIR))

# Change CWD to backend so Flask's template_folder and static_folder resolve
os.chdir(str(_BACKEND_DIR))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s - %(message)s")

print("=" * 60)
print("1. yolo_service import check")
print("=" * 60)
from services.yolo_service import (
    run_on_images, build_detection_index, _get_model, _bbox_to_pct, CLASS_NAMES
)
print("   OK — CLASS_NAMES:", list(CLASS_NAMES.values()))

print()
print("=" * 60)
print("2. YOLO model load check")
print("=" * 60)
model = _get_model()
print("   OK — model type:", type(model).__name__)

print()
print("=" * 60)
print("3. Bbox percentage conversion check")
print("=" * 60)
pct = _bbox_to_pct(100, 50, 300, 250, 640, 480)
print("   Input : x1=100, y1=50, x2=300, y2=250, w=640, h=480")
print("   Output:", pct)
expected = {"top": "10.42%", "left": "15.62%", "width": "31.25%", "height": "41.67%"}
for k, v in expected.items():
    assert pct[k] == v, f"FAIL {k}: expected {v}, got {pct[k]}"
print("   Assertions passed.")

print()
print("=" * 60)
print("4. gemini_service import check")
print("=" * 60)
from services.gemini_service import analyze_vehicle, _validate_gemini_response
print("   OK")

print()
print("=" * 60)
print("5. Gemini response schema validation check")
print("=" * 60)
mock_response = {
    "overall_severity": "Moderate",
    "summary": "Test summary",
    "damages": [
        {
            "part": "Front Bumper",
            "damage_type": "Dented",
            "severity": "Medium",
            "description": "Dent observed",
            "action": "Repair",
            "confidence": 87,
            "source_detection_ids": ["img_00_det_00"]
        }
    ],
    "recommendations": ["Physical inspection recommended."]
}
validated = _validate_gemini_response(mock_response)
assert validated["damages"][0]["severity"] == "Medium"
assert validated["overall_severity"] == "Moderate"
print("   Assertions passed.")

print()
print("=" * 60)
print("6. assessment_service import check")
print("=" * 60)
from services.assessment_service import run_assessment, _select_primary_image, _SEVERITY_STYLES
print("   OK — Severity styles:", list(_SEVERITY_STYLES.keys()))

print()
print("=" * 60)
print("7. Detection ID schema check")
print("=" * 60)
mock_yolo = [
    {
        "image_path": "/uploads/test.jpg",
        "image_filename": "test.jpg",
        "img_width": 640,
        "img_height": 480,
        "detections": [
            {
                "detection_id": "img_00_det_00",
                "class_id": 2,
                "class_name": "Dented",
                "confidence": 0.87,
                "bbox_abs": [100.0, 50.0, 300.0, 250.0],
                "bbox_pct": {"top": "10.42%", "left": "15.63%", "width": "31.25%", "height": "41.67%"},
                "polygon": None
            }
        ]
    }
]
idx = build_detection_index(mock_yolo)
assert "img_00_det_00" in idx
assert idx["img_00_det_00"]["class_name"] == "Dented"
print("   Detection index OK:", list(idx.keys()))

print()
print("=" * 60)
print("8. app.py import check")
print("=" * 60)
import app
print("   OK — _AI_PIPELINE_AVAILABLE:", app._AI_PIPELINE_AVAILABLE)

print()
print("=" * 60)
print("ALL CHECKS PASSED")
print("=" * 60)

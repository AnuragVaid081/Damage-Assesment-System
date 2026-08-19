import json
import shutil
from pathlib import Path

import cv2

# -----------------------------
# Paths
# -----------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_DIR = PROJECT_ROOT/"VehiDD"
IMAGE_DIR = DATASET_DIR/"image"/"image"

OUTPUT_DIR = PROJECT_ROOT/"ai"/"data"

# -----------------------------
# Class mapping
# -----------------------------

CLASS_MAP = {
    "mat_bo_phan": 0,  # Lost Parts
    "rach": 1,         # Torn
    "mop_lom": 2,      # Dented
    "tray_son": 3,    # Paint Scratches
    "thung": 4,        # Puncture
    "vo_kinh": 5,     # Broken Glass
    "be_den": 6,       # Broken Lamp
}


# -----------------------------
# Dataset splits
# -----------------------------

SPLITS = {
    "train": DATASET_DIR / 
}
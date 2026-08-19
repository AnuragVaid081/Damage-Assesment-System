import json
import shutil
from pathlib import Path

import cv2

# -----------------------------
# Paths
# -----------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_DIR = PROJECT_ROOT/"data"/"kaggle"/"vehide"
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
    "train": DATASET_DIR / "0Train_via_annos.json",
    "val": DATASET_DIR / "0Val_via_annos.json",
}

def convert_polygon(region, image_width, image_height):
    """Convert VIA polygon coordinates to YOLO segmentation format."""

    xs = region["all_x"]
    ys = region["all_y"]

    if len(xs) != len(ys):
        raise ValueError("X/Y Coordinate mismatch.")

    if len(xs) < 3:
        raise ValueError("Polygon contains fewer than 3 coordinates.")

    class_name = region["class"]

    if class_name not in CLASS_MAP:
        raise ValueError(f"Unknown Class: {class_name}")
    
    class_id = CLASS_MAP[class_name]

    coordinates = []

    for x, y in zip(xs,ys):

        # Clamp coordiantes to image boundaries
        x = max(0, min(x, image_width - 1))
        y = max (0, min(y, image_height - 1))

        # Normalize

        x_norm = x / image_width
        y_norm = y / image_height

        coordinates.extend([x_norm, y_norm])

    return class_id, coordinates


def process_split(split_name, annotation_file):

    print(f"\nProcessing {split_name} split...")

    # Output Directories
    image_output = OUTPUT_DIR / "images" / split_name
    label_output = OUTPUT_DIR / "labels" / split_name

    image_output.mkdir(parents=True,exist_ok=True)
    label_output.mkdir(parents=True,exist_ok=True)

    # Load annotations
    with open(annotation_file, "r", encoding = "utf-8") as f:
        annotations = json.load(f)

    processed = 0
    skipped = 0
    annotation_count = 0

    for entry in annotations.values():

        image_name = entry["name"]

        source_image = IMAGE_DIR / image_name

        if not source_image.exists():
            # print(f"Missing image: {image_name}")
            skipped += 1
            continue 

        image = cv2.imread(str(source_image))

        if image is None:
            print(f"Could not read image: {image_name}")
            skipped += 1
            continue

        height, width = image.shape[:2]

        label_lines = []

        for region in entry.get("regions", []):

            try:
                class_id, coordinates = convert_polygon(
                    region,
                    width,
                    height
                )

                line = "".join(
                    [str(class_id)] + 
                    [f"{value:.6f}" for value in coordinates]
                )

                label_lines.append(line)

                annotation_count += 1

            except ValueError as error:
                print(
                    f"Skipping annotation in {image_name}: {error}" 
                )


        # Copy image 
        destination_image = image_output / image_name

        shutil.copy2(
            source_image,
            destination_image
        )

        # Create label file
        label_file = label_output / f"{Path(image_name).stem}.txt"

        with open(label_file, "w", encoding = "utf-8") as f:
            f.write("\n".join(label_lines))

        processed += 1

        if processed % 500 == 0:
            print(f"Processed {processed} images...")

        print(f"{split_name}:")
        print(f" Images Processed: {processed}")
        print(f" Images skipped: {skipped}")
        print(f" Images Annotated: {annotation_count}")

def create_yaml():

    yaml_content = """path ../vehide_yolo
    
train: images/train
val: images/val

names:
    0: Lost Parts
    1: Torn
    2: Dented
    3: Paint Scratches
    4: Puncture
    5: Broken Glass
    6: Broken Lamp
""" 


    yaml_file = OUTPUT_DIR / "data.yaml"

    with open(yaml_file,"w",encoding = "utf-8") as f:
        f.write(yaml_content)


    print(f"\nCreated: {yaml_file}")

def main():

    print("VehiDD → YOLO Segmentation")
    print("=" * 40)

    for split_name, annotation_file in SPLITS.items():
        process_split(
            split_name,
            annotation_file,
        )

    create_yaml()

    print("\n Conversion Complete.")

if __name__ == "__main__" :
    main()
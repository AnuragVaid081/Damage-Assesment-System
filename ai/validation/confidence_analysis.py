from pathlib import Path
from collections import Counter

from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL = (
    PROJECT_ROOT
    / "runs"
    / "segment"
    / "ai"
    / "runs"
    / "yolo11n-baseline-8"
    / "weights"
    / "best.pt"
)

SOURCE = (
    PROJECT_ROOT
    / "ai"
    / "data"
    / "vehide_yolo"
    / "images"
    / "val"
)


CLASS_NAMES = {
    0: "Lost Parts",
    1: "Torn",
    2: "Dented",
    3: "Paint Scratches",
    4: "Puncture",
    5: "Broken Glass",
    6: "Broken Lamp",
}


def main():

    model = YOLO(str(MODEL))

    for conf in [0.50, 0.25, 0.10, 0.05]:

        counts = Counter()
        images_with_predictions = 0

        results = model.predict(
            source=str(SOURCE),
            imgsz=640,
            conf=conf,
            device=0,
            verbose=False,
            stream=True,
        )

        for result in results:

            if result.boxes is None or len(result.boxes) == 0:
                continue

            images_with_predictions += 1

            classes = result.boxes.cls.cpu().numpy() #type: ignore

            for class_id in classes:
                counts[int(class_id)] += 1

        print(f"\n=== CONFIDENCE: {conf} ===")
        print(f"Images with predictions: {images_with_predictions}")
        print(f"Total predictions: {sum(counts.values())}")

        for class_id, name in CLASS_NAMES.items():
            print(
                f"{name:<18} "
                f"{counts[class_id]:>6}"
            )


if __name__ == "__main__":
    main()
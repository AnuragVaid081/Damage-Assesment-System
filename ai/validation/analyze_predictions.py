from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[2]

LABEL_DIR = (
    PROJECT_ROOT
    / "ai"
    / "validation"
    / "baseline_predictions"
    / "predictions"
    / "labels"
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

    counts = Counter()
    images_with_predictions = set()

    label_files = list(LABEL_DIR.glob("*.txt"))

    for label_file in label_files:

        images_with_predictions.add(label_file.stem)

        with open(label_file, "r", encoding="utf-8") as f:

            for line in f:

                values = line.strip().split()

                if not values:
                    continue

                class_id = int(values[0])
                counts[class_id] += 1

    print("\n=== PREDICTION SUMMARY ===")

    print(f"Images with predictions: {len(images_with_predictions)}")
    print(f"Label files: {len(label_files)}")
    print(f"Total predicted instances: {sum(counts.values())}")

    print("\n=== PREDICTED CLASSES ===")

    for class_id, name in CLASS_NAMES.items():

        print(
            f"{class_id}: "
            f"{name:<18} "
            f"{counts[class_id]:>6}"
        )


if __name__ == "__main__":
    main()
from pathlib import Path

from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    PROJECT_ROOT
    /"runs"
    /"segment"
    /"ai"
    /"runs"
    /"yolo11n-baseline-8"
    /"weights"
    /"best.pt"
) 

SOURCE = (
    PROJECT_ROOT
    /"ai"
    /"data"
    /"vehide_yolo"
    /"images"
    /"val"
)

OUTPUT = PROJECT_ROOT / "ai" / "validation" / "baseline_predictions"

def main():

    print("Model:", MODEL_PATH)
    print("Model Exists:", MODEL_PATH.exists())

    print("Validation Images:", SOURCE)
    print("Images Exist:", SOURCE.exists())

    model = YOLO(str(MODEL_PATH))

    model.predict(
        source= str(SOURCE),
        imgsz = 640,
        conf = 0.25,
        device = 0,
        save = True,
        save_txt = True,
        save_conf = True,
        project = str(OUTPUT),
        name = "predictions",
        exist_ok = True
    )


if __name__ == "__main__":
    main()
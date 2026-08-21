from ultralytics import YOLO

def main():
    model = YOLO("yolo11n-seg.pt")

    model.train(
        data = "ai/data/vehide_yolo/data.yaml",
        epochs = 50,
        imgsz = 640,
        batch = 8,
        device = 0,
        workers = 4,
        project = "ai/runs",
        name = "yolo11n-baseline",
        pretrained = True,
        patience = 10,
        save = True,
        plots = True 
    )

if __name__ == "__main__":
    main()
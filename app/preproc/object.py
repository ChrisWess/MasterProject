from ultralytics import YOLO

yolo_model = YOLO("app/preproc/yolo_models/yolov8m.pt")
model_labels = yolo_model.names
cls_keys = tuple(model_labels.keys())
cls_vals = tuple(model_labels.values())


def detect_objects(img, classes=None):
    # Using PIL image
    if classes is not None:
        if type(classes) is not list:
            classes = list(classes)
        i = 0
        for cls in classes:
            if type(cls) is str:
                try:
                    classes[i] = cls_keys[cls_vals.index(cls)]
                except ValueError:
                    del classes[i]
                    continue
            elif cls >= len(model_labels):
                del classes[i]
                continue
            i += 1
    results = yolo_model.predict(source=img, save=False, stream=False, verbose=False, classes=classes)

    for result in results:
        # Detection
        bboxs = result.boxes
        for bbox, cls in zip(bboxs.xyxy, bboxs.cls):
            bbox = bbox.cpu()  # box with xyxy format, (N, 4)
            cls = cls.item()  # class, (N, 1)
            yield tuple(int(coord) for coord in bbox), model_labels[int(cls)]
        # result.boxes.conf  # confidence score, (N, 1)

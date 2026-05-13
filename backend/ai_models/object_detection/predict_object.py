import torch
import torchvision.transforms as T
import cv2
import numpy as np
from ai_models.object_detection.model_fastercnn import get_faster_rcnn_model
from core.config import settings

THRESHOLD = settings.DETECTION_THRESHOLD


def load_model_detection(device, model_path=str):
    model = get_faster_rcnn_model(num_classes=2)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()
    return model


def inference_faster_rcnn(model, input_data, device):
    # ================= LOAD IMAGE =================
    if isinstance(input_data, str):
        image = cv2.imread(input_data)
        if image is None:
            raise ValueError(f"Không đọc được ảnh từ path: {input_data}")
    else:
        # Assume it's a numpy array
        image = input_data

    orig = image.copy()

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    transform = T.Compose([
        T.ToTensor()
    ])

    image_tensor = transform(image_rgb).to(device)

    # ================= PREDICT =================
    with torch.no_grad():
        outputs = model([image_tensor])[0]

    boxes = outputs["boxes"].cpu().numpy()
    scores = outputs["scores"].cpu().numpy()
    labels = outputs["labels"].cpu().numpy()

    results = []

    # ================= DRAW =================
    for box, score, label in zip(boxes, scores, labels):
        if score < THRESHOLD:
            continue

        x1, y1, x2, y2 = map(int, box)

        # cv2.rectangle(orig, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # text = f"Opacity {score:.2f}"
        # cv2.putText(
        #     orig,
        #     text,
        #     (x1, y1 - 10),
        #     cv2.FONT_HERSHEY_SIMPLEX,
        #     0.6,
        #     (0, 255, 0),
        #     2
        # )

        results.append({
            "bbox": [x1, y1, x2, y2],
            "score": float(score),
            "label": int(label)
        })

    # BGR -> RGB
    result_image = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)
    return result_image, results
    



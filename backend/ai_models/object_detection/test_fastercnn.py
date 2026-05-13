import torch
import torchvision.transforms as T
import cv2
import numpy as np

from model_fastercnn import get_faster_rcnn_model

# ==============================
# CONFIG
# ==============================
import time
start = time.time()
a = "0a6a5956-58cf-4f17-9e39-7e0d17310f67"
MODEL_PATH = r"D:\doan\backend\prj-lung-disease-xray\model-ai\object_detection\best-model\object_detection_v1_crop_faster_cnn_best.pth"
IMAGE_PATH = fr"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_object\crop\crop_faster_rcnn\images\test\{a}.jpg"   # <-- đổi thành ảnh của bạn
THRESHOLD = 0.5

# ==============================
# LOAD MODEL
# ==============================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = get_faster_rcnn_model(num_classes=2)
model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model.to(device)
model.eval()

print("✅ Model loaded!")

# ==============================
# LOAD IMAGE
# ==============================
image = cv2.imread(IMAGE_PATH)
orig = image.copy()

# BGR -> RGB
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

# To tensor
transform = T.Compose([
    T.ToTensor()
])

image_tensor = transform(image).to(device)

# ==============================
# PREDICT
# ==============================
with torch.no_grad():
    outputs = model([image_tensor])

outputs = outputs[0]

boxes = outputs['boxes'].cpu().numpy()
scores = outputs['scores'].cpu().numpy()
labels = outputs['labels'].cpu().numpy()

# ==============================
# VISUALIZE
# ==============================
for box, score, label in zip(boxes, scores, labels):
    if score < THRESHOLD:
        continue
    
    x1, y1, x2, y2 = map(int, box)
    
    # Vẽ bounding box
    cv2.rectangle(orig, (x1, y1), (x2, y2), (0, 255, 0), 2)
    
    # Text
    text = f"Opacity {score:.2f}"
    cv2.putText(orig, text, (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

# ==============================
# SHOW RESULT
# ==============================
import matplotlib.pyplot as plt

# BGR -> RGB
img_rgb = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)

end = time.time()
print(f"Execution time: {end - start:.2f} seconds")

plt.imshow(img_rgb)
plt.title("Result")
plt.axis("off")
plt.show()
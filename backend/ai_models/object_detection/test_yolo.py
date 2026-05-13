from ultralytics import YOLO
import matplotlib.pyplot as plt
import cv2

model = YOLO(r"D:\doan\backend\prj-lung-disease-xray\model-ai\object_detection\best-model\best.pt")
a = "0a6a5956-58cf-4f17-9e39-7e0d17310f67"
result = model.predict(
    source=fr"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_object\crop\crop_yolo\images\test\{a}.jpg",  # <-- 1 ảnh
    conf=0.25,
    save=False
)[0]  # lấy phần tử đầu tiên

# vẽ bbox
img = result.plot()

# BGR -> RGB
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

plt.imshow(img_rgb)
plt.axis('off')
plt.title("YOLO Detection")
plt.show()
import os
import pandas as pd
import cv2

# ====== PATH ======
csv_path = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna-pneumonia-detection-challenge\stage_2_train_labels.csv"
image_dir = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna-pneumonia-detection-challenge\rsna_pneumonia_png"
output_dir = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna-pneumonia-detection-challenge\rsna_bbox_output"

os.makedirs(output_dir, exist_ok=True)

# ====== LOAD CSV ======
df = pd.read_csv(csv_path)

# ====== LỌC TARGET = 1 ======
df = df[df["Target"] == 1]

# ====== GROUP THEO patientId ======
grouped = df.groupby("patientId")

# ====== LOOP ======
for patient_id, group in grouped:
    img_path = os.path.join(image_dir, patient_id + ".png")
    
    if not os.path.exists(img_path):
        continue

    img = cv2.imread(img_path)

    # Vẽ tất cả bbox của patient này
    for _, row in group.iterrows():
        x = int(row["x"])
        y = int(row["y"])
        w = int(row["width"])
        h = int(row["height"])

        # vẽ rectangle (màu đỏ)
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)

    # lưu ảnh
    output_path = os.path.join(output_dir, patient_id + ".png")
    cv2.imwrite(output_path, img)

print("Done! ✅")
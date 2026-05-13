import os
import shutil
import pickle

# =========================
# CONFIG
# =========================
DATASET_DIR = r"D:\doan\dataset\rsna_classification_dataset\data_raw"

# File pkl chứa split
SPLIT_FILE = r"D:\doan\backend\prj-lung-disease-xray\backend\ai_models\classification\model_best\3_class\crop\densse\data_split_by_name (4).pkl"

# Folder output chứa ảnh test
OUTPUT_DIR = r"D:\doan\backend\prj-lung-disease-xray\dataset\test_dataset"

# =========================
# LOAD SPLIT FILE
# =========================
with open(SPLIT_FILE, "rb") as f:
    split_names = pickle.load(f)

test_filenames = split_names["test"]

# =========================
# TẠO FOLDER CLASS
# =========================
classes = ["0", "1", "2"]

for cls in classes:
    os.makedirs(os.path.join(OUTPUT_DIR, cls), exist_ok=True)

# =========================
# COPY ẢNH TEST
# =========================
copied_count = 0

for cls in classes:
    class_dir = os.path.join(DATASET_DIR, cls)

    for filename in os.listdir(class_dir):

        if filename in test_filenames:
            src_path = os.path.join(class_dir, filename)
            dst_path = os.path.join(OUTPUT_DIR, cls, filename)

            shutil.copy2(src_path, dst_path)
            copied_count += 1

print(f"✅ Đã copy {copied_count} ảnh test vào:")
print(OUTPUT_DIR)
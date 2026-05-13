import os
import cv2
import uuid
import albumentations as A

# ==============================
# CONFIG
# ==============================
IMAGE_DIR = "images"         # thư mục ảnh gốc
LABEL_DIR = "labels"         # thư mục label YOLO (.txt)
OUTPUT_IMG_DIR = "output/images"
OUTPUT_LBL_DIR = "output/labels"

os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)
os.makedirs(OUTPUT_LBL_DIR, exist_ok=True)

# ==============================
# AUGMENTATION PIPELINE
# ==============================
transform = A.Compose(
    [
        A.HorizontalFlip(p=0.5),
        A.ShiftScaleRotate(
            shift_limit=0.05,
            scale_limit=0.1,
            rotate_limit=10,
            p=0.7
        ),
        A.RandomBrightnessContrast(p=0.5),
        A.GaussNoise(p=0.2),
    ],
    bbox_params=A.BboxParams(
        format='yolo',   # YOLO format (x_center, y_center, w, h)
        label_fields=['class_labels'],
        min_visibility=0.3
    )
)

# ==============================
# LOAD YOLO LABEL
# ==============================
def load_yolo_label(label_path):
    bboxes = []
    class_labels = []

    if not os.path.exists(label_path):
        return bboxes, class_labels

    with open(label_path, "r") as f:
        for line in f.readlines():
            parts = line.strip().split()
            cls = int(parts[0])
            bbox = list(map(float, parts[1:]))

            class_labels.append(cls)
            bboxes.append(bbox)

    return bboxes, class_labels

# ==============================
# SAVE YOLO LABEL
# ==============================
def save_yolo_label(path, bboxes, class_labels):
    with open(path, "w") as f:
        for bbox, cls in zip(bboxes, class_labels):
            line = str(cls) + " " + " ".join(map(str, bbox))
            f.write(line + "\n")

# ==============================
# MAIN AUGMENT LOOP
# ==============================
def augment_dataset():
    image_files = [f for f in os.listdir(IMAGE_DIR) if f.endswith((".jpg", ".png"))]

    total = 0

    for img_name in image_files:
        img_path = os.path.join(IMAGE_DIR, img_name)
        lbl_path = os.path.join(LABEL_DIR, img_name.replace(".jpg", ".txt").replace(".png", ".txt"))

        image = cv2.imread(img_path)
        h, w = image.shape[:2]

        bboxes, class_labels = load_yolo_label(lbl_path)

        # ==========================
        # 1. COPY ẢNH GỐC
        # ==========================
        base_name = img_name.split(".")[0]

        new_img_name = f"{base_name}_orig.jpg"
        new_lbl_name = f"{base_name}_orig.txt"

        cv2.imwrite(os.path.join(OUTPUT_IMG_DIR, new_img_name), image)
        save_yolo_label(os.path.join(OUTPUT_LBL_DIR, new_lbl_name), bboxes, class_labels)

        total += 1

        # ==========================
        # 2. TẠO 3 AUGMENT
        # ==========================
        for i in range(3):
            augmented = transform(
                image=image,
                bboxes=bboxes,
                class_labels=class_labels
            )

            aug_img = augmented["image"]
            aug_bboxes = augmented["bboxes"]
            aug_labels = augmented["class_labels"]

            # skip nếu mất hết bbox
            if len(aug_bboxes) == 0:
                continue

            uid = str(uuid.uuid4())[:8]

            new_img_name = f"{base_name}_aug_{i}_{uid}.jpg"
            new_lbl_name = f"{base_name}_aug_{i}_{uid}.txt"

            cv2.imwrite(os.path.join(OUTPUT_IMG_DIR, new_img_name), aug_img)
            save_yolo_label(os.path.join(OUTPUT_LBL_DIR, new_lbl_name), aug_bboxes, aug_labels)

            total += 1

    print(f"✅ DONE! Tổng số ảnh: {total}")


if __name__ == "__main__":
    augment_dataset()
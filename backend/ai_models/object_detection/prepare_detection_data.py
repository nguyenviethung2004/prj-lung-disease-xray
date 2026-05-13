import os
import shutil
import pandas as pd
import pickle
from PIL import Image
from tqdm import tqdm

# ==========================================
# 1. CẤU HÌNH ĐƯỜNG DẪN & ĐỊNH DẠNG
# ==========================================
# CHỌN ĐỊNH DẠNG BẠN MUỐN XUẤT RA: 'yolo' hoặc 'faster_rcnn'
LABEL_FORMAT = 'yolo'  # Thay đổi thành 'yolo' nếu bạn muốn định dạng YOLO

PKL_FILE = r"D:\doan\backend\prj-lung-disease-xray\model-ai\classification\model_best\3_class\crop\densse\data_split_by_name (4).pkl"
CSV_FILE = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna-pneumonia-detection-challenge\stage_2_train_labels.csv"
SOURCE_IMG_DIR = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_classification_dataset\data_raw\2" 

# Thư mục đích sẽ tự động đổi tên theo định dạng để bạn không bị nhầm lẫn
OUTPUT_DIR = rf"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_object\raw\raw_{LABEL_FORMAT}"

# ==========================================
# 2. CÁC HÀM XỬ LÝ LABEL (YOLO & FASTER R-CNN)
# ==========================================
def get_yolo_label(x, y, w, h, img_width, img_height):
    """
    Format của YOLO: [class_id] [x_center] [y_center] [width] [height]
    Tất cả đều phải chuẩn hóa về dải [0, 1]. Class bệnh bắt đầu từ 0.
    """
    x_center = (x + w / 2) / img_width
    y_center = (y + h / 2) / img_height
    w_norm = w / img_width
    h_norm = h / img_height
    
    return f"0 {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}\n"

def get_faster_rcnn_label(x, y, w, h):
    """
    Format file txt tự chế cho Faster R-CNN: [class_id] [xmin] [ymin] [xmax] [ymax]
    Dùng tọa độ Pixel thật. Class bệnh bắt đầu từ 1 (vì 0 là Background).
    """
    xmin = x
    ymin = y
    xmax = x + w
    ymax = y + h
    
    return f"0 {xmin:.2f} {ymin:.2f} {xmax:.2f} {ymax:.2f}\n"

# ==========================================
# 3. HÀM TẠO CẤU TRÚC THƯ MỤC
# ==========================================
def create_dir_structure(base_dir):
    for folder in ['images', 'labels']:
        for split in ['train', 'val', 'test']:
            os.makedirs(os.path.join(base_dir, folder, split), exist_ok=True)
    print(f"📁 Đã tạo xong cấu trúc thư mục tại: {base_dir}")

# ==========================================
# 4. CHƯƠNG TRÌNH CHÍNH
# ==========================================
def main():
    print(f"🚀 Chế độ xuất Label: {LABEL_FORMAT.upper()}")
    create_dir_structure(OUTPUT_DIR)

    # Đọc PKL và loại bỏ đuôi '.jpg' để lấy đúng patientId
    print("⏳ Đang nạp file PKL...")
    with open(PKL_FILE, 'rb') as f:
        split_names = pickle.load(f)
    
    def extract_id(filename_list):
        return set([os.path.splitext(f)[0] for f in filename_list])

    train_ids = extract_id(split_names['train'])
    val_ids = extract_id(split_names['val'])
    test_ids = extract_id(split_names['test'])

    # Đọc CSV và CHỈ LẤY TARGET == 1
    print("⏳ Đang nạp và lọc file CSV (Chỉ lấy Target = 1)...")
    df = pd.read_csv(CSV_FILE)
    df_positive = df[df['Target'] == 1].copy()

    # Gom nhóm theo từng bệnh nhân
    grouped = df_positive.groupby('patientId')
    print(f"🔍 Tìm thấy {len(grouped)} bệnh nhân có vết mờ. Bắt đầu xử lý...")

    missing_images = 0
    success_count = {'train': 0, 'val': 0, 'test': 0}

    for patient_id, group in tqdm(grouped, desc="Đang Copy & Convert"):
        # 1. Xác định ID thuộc tập nào
        if patient_id in train_ids:
            split = 'train'
        elif patient_id in val_ids:
            split = 'val'
        elif patient_id in test_ids:
            split = 'test'
        else:
            continue

        # 2. Kiểm tra ảnh gốc
        src_img_path = os.path.join(SOURCE_IMG_DIR, f"{patient_id}.png")
        if not os.path.exists(src_img_path):
            missing_images += 1
            continue

        # 3. Lấy kích thước ảnh (Chỉ thực sự cần thiết nếu dùng YOLO)
        img_width, img_height = 1, 1 # Mặc định
        if LABEL_FORMAT == 'yolo':
            with Image.open(src_img_path) as img:
                img_width, img_height = img.size

        # 4. Copy ảnh sang thư mục mới
        dst_img_path = os.path.join(OUTPUT_DIR, 'images', split, f"{patient_id}.jpg")
        if not os.path.exists(dst_img_path):
            shutil.copy(src_img_path, dst_img_path)

        # 5. Ghi file Label
        txt_path = os.path.join(OUTPUT_DIR, 'labels', split, f"{patient_id}.txt")
        
        with open(txt_path, 'w') as f:
            for _, row in group.iterrows():
                x = float(row['x'])
                y = float(row['y'])
                w = float(row['width'])
                h = float(row['height'])

                # Gọi hàm xuất format tương ứng
                if LABEL_FORMAT == 'yolo':
                    line = get_yolo_label(x, y, w, h, img_width, img_height)
                else:
                    line = get_faster_rcnn_label(x, y, w, h)
                
                f.write(line)
        
        success_count[split] += 1

    print("\n✅ HOÀN TẤT TẠO DATASET!")
    print(f"📊 Thống kê số lượng ảnh (Định dạng: {LABEL_FORMAT.upper()}):")
    print(f"   - Train : {success_count['train']} ảnh")
    print(f"   - Val   : {success_count['val']} ảnh")
    print(f"   - Test  : {success_count['test']} ảnh")
    print(f"💾 Dữ liệu được lưu tại: {OUTPUT_DIR}")
    
    if missing_images > 0:
        print(f"⚠️ Cảnh báo: Có {missing_images} ảnh bị thiếu trong thư mục gốc.")

if __name__ == '__main__':
    main()
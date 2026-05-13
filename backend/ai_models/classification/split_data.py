import os
import shutil
import pandas as pd

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN (Bạn có thể tùy chỉnh lại nếu cần)
# ==========================================
SOURCE_DIR = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna-pneumonia-detection-challenge\rsna_pneumonia_png"
# Thư mục đích để chứa 3 folder 0, 1, 2 (Tự động tạo nếu chưa có)
OUTPUT_DIR = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_classification_dataset" 
# Đường dẫn tới file csv chứa thông tin class (thường là file stage_2_detailed_class_info.csv)
CSV_PATH = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna-pneumonia-detection-challenge\stage_2_detailed_class_info.csv"

# Dictionary để map tên class thành tên thư mục (0, 1, 2)
CLASS_MAPPING = {
    "Normal": "0",
    "No Lung Opacity / Not Normal": "1",
    "Lung Opacity": "2"
}

def split_dataset():
    # 1. Tạo các thư mục đích (0, 1, 2)
    print("Đang tạo các thư mục đích...")
    for folder_name in CLASS_MAPPING.values():
        os.makedirs(os.path.join(OUTPUT_DIR, folder_name), exist_ok=True)

    # 2. Đọc file CSV
    print(f"Đang đọc dữ liệu từ {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)

    # Xóa các dòng trùng lặp (1 ảnh có nhiều bounding box sẽ sinh ra nhiều dòng)
    df = df.drop_duplicates(subset=['patientId', 'class'])

    # Biến đếm để thống kê
    success_count = 0
    missing_count = 0

    print("Bắt đầu phân loại và copy ảnh. Vui lòng đợi...")
    
    # 3. Lặp qua từng dòng trong dataframe và copy ảnh
    for index, row in df.iterrows():
        patient_id = row['patientId']
        class_name = row['class']

        # Xử lý tên file và đường dẫn
        file_name = f"{patient_id}.png"
        source_path = os.path.join(SOURCE_DIR, file_name)

        # Bỏ qua nếu class name không nằm trong mapping
        if class_name not in CLASS_MAPPING:
            continue

        target_folder = CLASS_MAPPING[class_name]
        target_path = os.path.join(OUTPUT_DIR, target_folder, file_name)

        # Thực hiện copy nếu file tồn tại
        if os.path.exists(source_path):
            # Dùng shutil.copy2 để giữ nguyên metadata của ảnh
            shutil.copy2(source_path, target_path)
            success_count += 1
        else:
            missing_count += 1
            
        # In tiến độ cho mỗi 2000 ảnh để dễ theo dõi
        if (index + 1) % 2000 == 0:
            print(f"Đã xử lý {index + 1} dòng...")

    # 4. In báo cáo tổng kết
    print("\n" + "="*40)
    print("✅ HOÀN TẤT PHÂN LOẠI ẢNH!")
    print(f"📁 Thư mục đầu ra: {OUTPUT_DIR}")
    print(f"✔️ Copy thành công: {success_count} ảnh")
    if missing_count > 0:
        print(f"⚠️ Không tìm thấy (thiếu file gốc): {missing_count} ảnh")
    print("="*40)

if __name__ == "__main__":
    split_dataset()
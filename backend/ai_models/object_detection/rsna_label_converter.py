import pandas as pd
import os

def convert_rsna_to_yolo(csv_path, output_dir):
    IMG_WIDTH = 1024.0
    IMG_HEIGHT = 1024.0
    
    # YOLO Class ID
    CLASS_ID = 2

    os.makedirs(output_dir, exist_ok=True)

    print(f"Reading CSV data from: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print("Error: CSV file not found. Please check your path.")
        return

    df_positive = df[df['Target'] == 1].copy()

    # YOLO format: normalized x_center, y_center, w, h
    df_positive['x_center'] = (df_positive['x'] + (df_positive['width'] / 2)) / IMG_WIDTH
    df_positive['y_center'] = (df_positive['y'] + (df_positive['height'] / 2)) / IMG_HEIGHT
    df_positive['w_norm'] = df_positive['width'] / IMG_WIDTH
    df_positive['h_norm'] = df_positive['height'] / IMG_HEIGHT

    print("Generating YOLO label files...")
    grouped = df_positive.groupby('patientId')
    
    count = 0
    for patient_id, group in grouped:
        txt_filename = os.path.join(output_dir, f"{patient_id}.txt")
        
        with open(txt_filename, 'w') as f:
            for _, row in group.iterrows():
                line = f"{CLASS_ID} {row['x_center']:.6f} {row['y_center']:.6f} {row['w_norm']:.6f} {row['h_norm']:.6f}\n"
                f.write(line)
        count += 1

    print(f"✅ YOLO Conversion complete! Successfully created {count} files in:\n{output_dir}\n")


def convert_rsna_to_faster_rcnn(csv_path, output_csv_path):
    """
    Faster R-CNN requires absolute coordinates: [xmin, ymin, xmax, ymax]
    and background class is strictly 0. 
    """
    print(f"Reading CSV data from: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print("Error: CSV file not found. Please check your path.")
        return

    # Chỉ lấy các hộp có viêm phổi (Target == 1)
    df_positive = df[df['Target'] == 1].copy()

    # Tính toán tọa độ xmin, ymin, xmax, ymax
    df_positive['xmin'] = df_positive['x']
    df_positive['ymin'] = df_positive['y']
    df_positive['xmax'] = df_positive['x'] + df_positive['width']
    df_positive['ymax'] = df_positive['y'] + df_positive['height']

    # Gán class_id. Faster RCNN quy định 0 là background, nên Target dùng 1 là hợp lý.
    df_positive['class_id'] = 1 

    # Lọc lại các cột cần thiết cho Faster R-CNN Dataloader
    faster_rcnn_df = df_positive[['patientId', 'xmin', 'ymin', 'xmax', 'ymax', 'class_id']]

    # Đảm bảo thư mục đầu ra tồn tại
    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    
    # Lưu ra file CSV mới
    faster_rcnn_df.to_csv(output_csv_path, index=False)
    print(f"✅ Faster R-CNN Conversion complete! Saved parsed bounding boxes to:\n{output_csv_path}")


if __name__ == "__main__":
    csv_path = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna-pneumonia-detection-challenge\stage_2_train_labels.csv"
    
    # Output path cho YOLO (thư mục chứa txt)
    yolo_output_dir = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_object\raw_yolo" 
    
    # Output path cho Faster R-CNN (chỉ cần 1 file CSV tổng hợp)
    faster_rcnn_output_csv = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_object\faster_rcnn_labels.csv"

    # Chạy convert YOLO
    convert_rsna_to_yolo(csv_path, yolo_output_dir)
    
    # Chạy convert Faster R-CNN
    convert_rsna_to_faster_rcnn(csv_path, faster_rcnn_output_csv)
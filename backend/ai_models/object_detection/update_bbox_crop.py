import os
import glob
import sys
import cv2
import torch
import numpy as np
import pandas as pd  # <-- Thêm pandas để đọc CSV
from PIL import Image
from torchvision import transforms

current_dir = os.path.dirname(os.path.abspath(__file__))

# Lùi lại 1 cấp để ra thư mục cha ('model-ai')
parent_dir = os.path.dirname(current_dir)

# Thêm thư mục 'model-ai' vào danh sách tìm kiếm của Python
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from segmentation.models import ResNet18UNet

def load_unet(model_path, device):
    """Khởi tạo và load trọng số U-Net"""
    model = ResNet18UNet(out_channels=2) 
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()
    return model

def get_unet_mask(image_rgb, model, device):
    """Chạy ảnh qua U-Net để lấy Mask trắng đen"""
    transform = transforms.Compose([
        transforms.Resize((512, 512)), 
        transforms.Grayscale(num_output_channels=1),
        transforms.ToTensor(),
    ])
    
    input_tensor = transform(image_rgb).unsqueeze(0).to(device)
    
    with torch.no_grad():
        output = model(input_tensor)
        
    if output.shape[1] == 1:
        prob = torch.sigmoid(output)
        mask = prob[0, 0].cpu().numpy()
        mask = (mask > 0.5).astype(np.uint8) * 255
    else:
        mask_tensor = torch.argmax(output, dim=1)
        mask = mask_tensor[0].cpu().numpy()
        mask = (mask > 0).astype(np.uint8) * 255

    return mask

def process_and_crop_image(img_path, model, device, padding_percent=0.05, min_area_ratio=0.15):
    """
    Xử lý 1 ảnh: Trả về ảnh đã crop VÀ tọa độ x_min, y_min để dịch chuyển Bounding Box
    """
    img_orig = cv2.imread(img_path)
    img_rgb = Image.fromarray(cv2.cvtColor(img_orig, cv2.COLOR_BGR2RGB))
    H_orig, W_orig = img_orig.shape[:2]
    
    mask_256 = get_unet_mask(img_rgb, model, device)
    mask_orig = cv2.resize(mask_256, (W_orig, H_orig), interpolation=cv2.INTER_NEAREST)
    
    mask_area = np.sum(mask_orig == 255)
    total_area = H_orig * W_orig
    area_ratio = mask_area / total_area
    
    # --- FALLBACK KHI MASK LỖI ---
    if area_ratio < min_area_ratio:
        print(f"⚠️ Cảnh báo: Mask quá nhỏ tại {os.path.basename(img_path)}. Dùng Center Crop!")
        pad_h, pad_w = int(H_orig * 0.1), int(W_orig * 0.1)
        cropped_img = img_orig[pad_h:H_orig-pad_h, pad_w:W_orig-pad_w]
        # Trả về thêm toạ độ x_min, y_min
        return cropped_img, pad_w, pad_h

    contours, _ = cv2.findContours(mask_orig, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hull_mask = np.zeros_like(mask_orig)
    
    for cnt in contours:
        if cv2.contourArea(cnt) > 500:
            hull = cv2.convexHull(cnt)
            cv2.drawContours(hull_mask, [hull], -1, 255, thickness=cv2.FILLED)
            
    final_contours, _ = cv2.findContours(hull_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not final_contours:
        return img_orig, 0, 0 # Fallback 0, 0
        
    all_points = np.vstack(final_contours)
    x, y, w, h = cv2.boundingRect(all_points)
    
    pad_x = int(W_orig * padding_percent)
    pad_y = int(H_orig * padding_percent)
    
    x_min = max(0, x - pad_x)
    y_min = max(0, y - pad_y)
    x_max = min(W_orig, x + w + pad_x)
    y_max = min(H_orig, y + h + pad_y)
    
    cropped_img = img_orig[y_min:y_max, x_min:x_max]
    
    # Trả về thêm toạ độ x_min, y_min để căn chỉnh lại bbox
    return cropped_img, x_min, y_min

def main():
    # --- CẤU HÌNH ĐƯỜNG DẪN ---
    input_dir = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_classification_dataset\data_raw\2"
    output_dir = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_classification_dataset\data_raw\2_crop"
    unet_model_path = r"D:\doan\backend\prj-lung-disease-xray\model-ai\segmentation\unet_resnet18\unet_resnet18.pt"
    
    # --- CẤU HÌNH CSV ---
    csv_path = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna-pneumonia-detection-challenge\stage_2_train_labels.csv"
    output_txt_path = os.path.join(output_dir, "cropped_labels_target1.txt")
    
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # 1. ĐỌC VÀ LỌC FILE CSV CHỈ LẤY TARGET = 1
    print("Đang đọc file CSV...")
    df = pd.read_csv(csv_path)
    df_target_1 = df[df['Target'] == 1].dropna(subset=['x', 'y', 'width', 'height'])
    
    # Tạo dictionary lưu các bboxes theo patientId
    # Format: {'patientId': [[x, y, w, h], [x2, y2, w2, h2]]}
    bbox_dict = {}
    for _, row in df_target_1.iterrows():
        pid = row['patientId']
        if pid not in bbox_dict:
            bbox_dict[pid] = []
        bbox_dict[pid].append([row['x'], row['y'], row['width'], row['height']])
        
    print(f"Tìm thấy {len(bbox_dict)} bệnh nhân có Target = 1 trong CSV.")

    print(f"Loading U-Net model from {unet_model_path}...")
    model = load_unet(unet_model_path, device)
    
    image_paths = glob.glob(os.path.join(input_dir, "*.jpg")) + \
                  glob.glob(os.path.join(input_dir, "*.png"))
                  
    print(f"Tìm thấy tổng cộng {len(image_paths)} ảnh trong thư mục.")
    
    processed_count = 0
    
    # Mở file txt để ghi (Chế độ 'w' sẽ tạo mới/ghi đè file)
    with open(output_txt_path, 'w') as f_out:
        # Ghi header format chuẩn
        f_out.write("patientId,x,y,width,height,Target\n")
        
        for idx, img_path in enumerate(image_paths):
            filename = os.path.basename(img_path)
            # Tách lấy tên patientId (bỏ đuôi .jpg, .png)
            patient_id = os.path.splitext(filename)[0]
            
            # --- CHỈ XỬ LÝ NHỮNG ẢNH CÓ TARGET = 1 ---
            if patient_id not in bbox_dict:
                continue
                
            out_path = os.path.join(output_dir, filename)
            
            try:
                # Trả về ảnh đã crop VÀ tọa độ góc trên cùng bên trái của vùng crop
                cropped_img, x_min, y_min = process_and_crop_image(img_path, model, device)
                cv2.imwrite(out_path, cropped_img)
                
                # Cập nhật lại tọa độ các bounding boxes cho ảnh này
                bboxes = bbox_dict[patient_id]
                for bbox in bboxes:
                    old_x, old_y, old_w, old_h = bbox
                    
                    # Tính tọa độ mới
                    new_x = float(old_x) - x_min
                    new_y = float(old_y) - y_min
                    
                    # Ép kiểu dữ liệu tránh bị âm nếu bounding box bị cắt một chút ngoài viền
                    new_x = max(0.0, new_x)
                    new_y = max(0.0, new_y)
                    
                    # Ghi vào file txt mới
                    f_out.write(f"{patient_id},{new_x},{new_y},{old_w},{old_h},1\n")
                
                processed_count += 1
                if processed_count % 50 == 0:
                    print(f"Đã xử lý và crop bbox: {processed_count} ảnh Target=1...")
                
            except Exception as e:
                print(f"❌ Lỗi tại ảnh {filename}: {e}")

    print(f"✅ Xong! Toàn bộ {processed_count} ảnh Target=1 đã được cắt và lưu vào: {output_dir}")
    print(f"✅ File nhãn mới đã được lưu tại: {output_txt_path}")

if __name__ == "__main__":
    main()
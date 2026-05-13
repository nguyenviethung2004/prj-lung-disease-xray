import os
import glob
import sys
import cv2
import torch
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Lùi lại 1 cấp để ra thư mục cha ('model-ai')
parent_dir = os.path.dirname(current_dir)

# 3. Thêm thư mục 'model-ai' vào danh sách tìm kiếm của Python
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
import numpy as np
from PIL import Image
from torchvision import transforms
from segmentation.src.models import ResNet18UNet # Lưu ý: Bạn cần import class UNet của bạn vào đây

# Lưu ý: Bạn cần import class UNet của bạn vào đây
# from your_unet_file import UNet 

def load_unet(model_path, device):
    """Khởi tạo và load trọng số U-Net"""
    # Thay UNet() bằng class U-Net thực tế của bạn
    # model = UNet(in_channels=3, out_channels=1) 
    
    # Ở đây tôi dùng một mock-up để code không bị lỗi, bạn nhớ thay bằng model thật
    model = ResNet18UNet(out_channels=2) 
    
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()
    return model

def get_unet_mask(image_rgb, model, device):
    """Chạy ảnh qua U-Net để lấy Mask trắng đen (0 và 255) cực kỳ an toàn"""
    transform = transforms.Compose([
        transforms.Resize((512, 512)), 
        transforms.Grayscale(num_output_channels=1), # Ép ảnh đầu vào về 1 kênh xám
        transforms.ToTensor(),
    ])
    
    input_tensor = transform(image_rgb).unsqueeze(0).to(device)
    
    with torch.no_grad():
        output = model(input_tensor)
        
    # --- XỬ LÝ AN TOÀN CHO MỌI LOẠI U-NET ---
    # Trường hợp 1: U-Net trả về 1 kênh (Sigmoid) -> shape: [1, 1, 512, 512]
    if output.shape[1] == 1:
        prob = torch.sigmoid(output)
        # Lấy chính xác phần tử [0, 0] để ra đúng ma trận 2D [512, 512]
        mask = prob[0, 0].cpu().numpy()
        mask = (mask > 0.5).astype(np.uint8) * 255
        
    # Trường hợp 2: U-Net trả về 2 kênh trở lên (CrossEntropy/Softmax) -> shape: [1, 2+, 512, 512]
    else:
        # Lấy nhãn có xác suất cao nhất (dim=1). Output mask sẽ thành shape: [1, 512, 512]
        mask_tensor = torch.argmax(output, dim=1)
        # Lấy phần tử [0] để ra ma trận 2D [512, 512]
        mask = mask_tensor[0].cpu().numpy()
        # Chuyển class 1 (phổi) thành màu trắng 255, class 0 (nền) thành màu đen 0
        mask = (mask > 0).astype(np.uint8) * 255

    return mask

def process_and_crop_image(img_path, model, device, padding_percent=0.05, min_area_ratio=0.15):
    """
    Xử lý 1 ảnh: Tìm Mask -> Convex Hull -> Bounding Box -> Crop
    Có bảo vệ khi Mask quá nhỏ.
    """
    # 1. Đọc ảnh gốc
    img_orig = cv2.imread(img_path)
    img_rgb = Image.fromarray(cv2.cvtColor(img_orig, cv2.COLOR_BGR2RGB))
    H_orig, W_orig = img_orig.shape[:2]
    
    # 2. Lấy Mask từ U-Net
    mask_256 = get_unet_mask(img_rgb, model, device)
    
    # Phóng to mask về lại kích thước ảnh gốc
    mask_orig = cv2.resize(mask_256, (W_orig, H_orig), interpolation=cv2.INTER_NEAREST)
    
    # 3. Tính diện tích Mask để kiểm tra lỗi Under-segmentation
    mask_area = np.sum(mask_orig == 255)
    total_area = H_orig * W_orig
    area_ratio = mask_area / total_area
    
    # --- CƠ CHẾ BẢO VỆ (FALLBACK) ---
    if area_ratio < min_area_ratio:
        print(f"⚠️ Cảnh báo: Mask quá nhỏ ({area_ratio:.1%}) tại {os.path.basename(img_path)}. Dùng Center Crop!")
        # Rơi vào trường hợp U-Net lỗi. Ta cắt bỏ 10% viền đen xung quanh ảnh gốc làm phương án an toàn.
        pad_h, pad_w = int(H_orig * 0.1), int(W_orig * 0.1)
        cropped_img = img_orig[pad_h:H_orig-pad_h, pad_w:W_orig-pad_w]
        return cropped_img

    # 4. Áp dụng Convex Hull (Sợi dây chun) để nối các Mask bị đứt gãy
    contours, _ = cv2.findContours(mask_orig, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hull_mask = np.zeros_like(mask_orig)
    
    for cnt in contours:
        if cv2.contourArea(cnt) > 500: # Bỏ qua rác nhỏ
            hull = cv2.convexHull(cnt)
            cv2.drawContours(hull_mask, [hull], -1, 255, thickness=cv2.FILLED)
            
    # 5. Tìm Bounding Box ôm trọn Mask đã được Convex Hull
    final_contours, _ = cv2.findContours(hull_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not final_contours:
        return img_orig # Fallback cuối cùng nếu không có gì
        
    # Gộp tất cả các contours lại để tìm 1 khung chữ nhật lớn nhất ôm cả 2 lá phổi
    all_points = np.vstack(final_contours)
    x, y, w, h = cv2.boundingRect(all_points)
    
    # 6. Thêm Padding (Lề) để không cắt phạm mép phổi
    pad_x = int(W_orig * padding_percent)
    pad_y = int(H_orig * padding_percent)
    
    # Ép giới hạn để không bị tràn ra ngoài viền ảnh
    x_min = max(0, x - pad_x)
    y_min = max(0, y - pad_y)
    x_max = min(W_orig, x + w + pad_x)
    y_max = min(H_orig, y + h + pad_y)
    
    # 7. Cắt ảnh (Crop)
    cropped_img = img_orig[y_min:y_max, x_min:x_max]
    
    return cropped_img

def main():
    # --- CẤU HÌNH ĐƯỜNG DẪN ---
    input_dir = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_classification_dataset\data_raw\4_covid"       # Thư mục chứa ảnh gốc
    output_dir = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_classification_dataset\data_raw\covid_crop"  # Thư mục lưu ảnh đã cắt
    unet_model_path = r"D:\doan\backend\prj-lung-disease-xray\model-ai\segmentation\unet_resnet18\unet_resnet18.pt"    # Đường dẫn file trọng số U-Net
    
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print(f"Loading U-Net model from {unet_model_path}...")
    model = load_unet(unet_model_path, device)
    
    # Quét toàn bộ ảnh jpg/png/jpeg trong thư mục
    image_paths = glob.glob(os.path.join(input_dir, "*.jpg")) + \
                  glob.glob(os.path.join(input_dir, "*.png"))
                  
    print(f"Tìm thấy {len(image_paths)} ảnh cần xử lý.")
    
    for idx, img_path in enumerate(image_paths):
        filename = os.path.basename(img_path)
        out_path = os.path.join(output_dir, filename)
        
        # Bỏ qua nếu ảnh đã được xử lý (Hữu ích khi chạy lại code bị gián đoạn)
        if os.path.exists(out_path):
            continue
            
        try:
            # Chạy pipeline cắt ảnh
            cropped_img = process_and_crop_image(img_path, model, device)
            
            # Lưu ảnh
            cv2.imwrite(out_path, cropped_img)
            
            if idx % 100 == 0:
                print(f"Đã xử lý: {idx}/{len(image_paths)} ảnh...")
            
        except Exception as e:
            print(f"❌ Lỗi tại ảnh {filename}: {e}")
    print("✅ Xong! Toàn bộ ảnh đã được cắt và lưu vào:", output_dir)

if __name__ == "__main__":
    main()
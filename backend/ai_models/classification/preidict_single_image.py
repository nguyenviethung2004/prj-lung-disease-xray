import os
import torch
import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from torchvision import transforms

# Thư viện Grad-CAM
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from pytorch_grad_cam.utils.image import show_cam_on_image

# Import mô hình của bạn (Đảm bảo file models.py cùng thư mục)
from models import RSNADenseNet121

# --- CẤU HÌNH ---
MODEL_PATH = r"D:\doan\backend\prj-lung-disease-xray\model-ai\classification\model_best\3_class\crop\densse\densenet_380_epoch_11.pth"
IMAGE_PATH = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_classification_dataset\rsna_cropped_images\2\0a62df77-7459-4acc-9cca-a62c2cec4b0f.png" # <<< ĐIỀN ĐƯỜNG DẪN ẢNH X-QUANG VÀO ĐÂY
IMAGE_SIZE = 380
CLASSES = ['Normal', 'COVID-19', 'Pneumonia'] # Class 0, 1, 2

def load_model(device):
    print("--- ĐANG TẢI MÔ HÌNH ---")
    model = RSNADenseNet121()
    checkpoint = torch.load(MODEL_PATH, map_location=device)
    
    if 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    elif 'state_dict' in checkpoint:
        model.load_state_dict(checkpoint['state_dict'])
    else:
        model.load_state_dict(checkpoint)
        
    model.to(device)
    model.eval() # Chuyển sang chế độ đánh giá
    return model

def process_xray_image(img_path, image_size):
    """Xử lý ảnh X-quang (ảnh xám) thành 3 kênh màu để đưa vào model"""
    
    # 1. XỬ LÝ ẢNH HIỂN THỊ CHO GRAD-CAM (NỀN)
    # Đọc ảnh X-quang bằng OpenCV. Dù là ảnh xám, cv2.IMREAD_COLOR (1) sẽ tự động nhân bản 1 kênh thành 3 kênh BGR
    img_bgr = cv2.imread(img_path, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError(f"Không thể đọc ảnh từ đường dẫn: {img_path}")
        
    # Chuyển BGR sang RGB cho Matplotlib và chuẩn hóa về [0, 1]
    rgb_img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    rgb_img = cv2.resize(rgb_img, (image_size, image_size))
    rgb_img = np.float32(rgb_img) / 255.0

    # 2. XỬ LÝ ẢNH CHO PYTORCH MODEL
    # MỞ RỘNG: Bạn MỘT MỰC PHẢI DÙNG đúng các thông số transform bạn đã dùng lúc train (trong file data_processing.py).
    # Thông thường, X-quang được chuyển sang RGB và dùng ImageNet Normalize.
    transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        # Lưu ý: Nếu lúc train bạn dùng Normalize khác, phải sửa lại dòng này!
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]) 
    ])
    
    # PIL mở ảnh và ép kiểu thành RGB (quan trọng cho ảnh X-quang vốn là Grayscale)
    pil_image = Image.open(img_path).convert('RGB')
    input_tensor = transform(pil_image).unsqueeze(0) # Output shape: (1, 3, 380, 380)
    
    return input_tensor, rgb_img

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Đang chạy trên: {device}")

    # 1. Tải mô hình và ảnh
    model = load_model(device)
    input_tensor, rgb_img = process_xray_image(IMAGE_PATH, IMAGE_SIZE)
    input_tensor = input_tensor.to(device)

    # 2. Dự đoán lớp (Inference)
    print("\n--- BẮT ĐẦU DỰ ĐOÁN ---")
    with torch.no_grad(): # Grad-CAM sẽ tự bật gradient lại cho input sau
        outputs = model(input_tensor)
        probabilities = torch.nn.functional.softmax(outputs[0], dim=0)
        conf, predicted_class = torch.max(probabilities, 0)
        
    class_idx = predicted_class.item()
    confidence = conf.item() * 100
    print(f"-> KẾT QUẢ: {CLASSES[class_idx]}")
    print(f"-> Độ tự tin: {confidence:.2f}%\n")

    # 3. Khởi tạo Grad-CAM
    # CHÚ Ý: Cấu hình target_layer cho DenseNet. 
    # Nếu file models.py của bạn dùng cấu trúc torchvision chuẩn:
    try:
        # Layer tích chập cuối cùng của DenseNet thường nằm ở features[-1] (tên là norm5)
        target_layers = [model.model.features[-1]]
    except AttributeError:
        # Nếu RSNADenseNet121 gói backbone vào một biến (vd: self.densenet)
        target_layers = [model.densenet.features[-1]]

    # Tạo đối tượng CAM
    cam = GradCAM(model=model, target_layers=target_layers)
    
    # Đặt target là class mô hình vừa dự đoán ra để xem nó chú ý vào đâu để ra quyết định này
    targets = [ClassifierOutputTarget(class_idx)]

    # Tính toán Heatmap
    grayscale_cam = cam(input_tensor=input_tensor, targets=targets)
    grayscale_cam = grayscale_cam[0, :] 

    # Trộn Heatmap lên ảnh gốc X-quang (Hiệu ứng overlay)
    visualization = show_cam_on_image(rgb_img, grayscale_cam, use_rgb=True)

    # 4. Hiển thị kết quả trực quan
    plt.figure(figsize=(15, 5))
    
    # Cột 1: Ảnh gốc
    plt.subplot(1, 3, 1)
    plt.imshow(rgb_img)
    plt.title("Phim X-quang Phổi Gốc")
    plt.axis('off')
    
    # Cột 2: Heatmap
    plt.subplot(1, 3, 2)
    plt.imshow(grayscale_cam, cmap='jet')
    plt.title("Vùng Tập Trung (Heatmap)")
    plt.axis('off')
    
    # Cột 3: Overlay (Gốc + Heatmap)
    plt.subplot(1, 3, 3)
    plt.imshow(visualization)
    plt.title(f"Dự đoán: {CLASSES[class_idx]} ({confidence:.1f}%)")
    plt.axis('off')
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
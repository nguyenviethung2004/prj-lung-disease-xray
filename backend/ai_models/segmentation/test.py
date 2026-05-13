import torch
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from torchvision import transforms
from models import ResNet18UNet 

# 1. Khởi tạo thiết bị
import time
start_time = time.time()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Đang sử dụng thiết bị: {device}")

# 2. Khởi tạo và Load Model
# Lưu ý: Đảm bảo class ResNet18UNet của bạn đã được code để nhận in_channels=1
unet = ResNet18UNet(out_channels=2) 
model_name = r"D:\doan\backend\prj-lung-disease-xray\model-ai\segmentation\unet_resnet18\unet_resnet18.pt"

# Load weights và chuyển model vào thiết bị
unet.load_state_dict(torch.load(model_name, map_location=device))
unet.to(device) # Sửa lỗi unet.to() bị trống
unet.eval()

# 3. Đọc và Tiền xử lý ảnh X-quang
image_path = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_classification_dataset\data_raw\2\0a0f91dc-6015-4342-b809-d19610854a21.png" # THAY ĐỔI ĐƯỜNG DẪN NÀY

# Đọc ảnh và chuyển ngay về ảnh xám (Grayscale - 1 channel)
try:
    image = Image.open(image_path).convert("L")
except FileNotFoundError:
    print(f"Không tìm thấy ảnh tại: {image_path}")
    exit()

# Khai báo các bước tiền xử lý
preprocess = transforms.Compose([
    transforms.Resize((512, 512)), # Resize ảnh về 512x512
    transforms.ToTensor(),         # Chuyển thành tensor và scale giá trị về [0, 1]
    # LƯU Ý: Nếu lúc train bạn có dùng Normalize (ví dụ mean=[0.5], std=[0.5]), 
    # hãy bỏ comment dòng dưới đây và điền đúng thông số:
    # transforms.Normalize(mean=[0.5], std=[0.5])
])

input_tensor = preprocess(image)
# Thêm batch dimension để shape biến thành [1, 1, 512, 512] (batch_size, channels, H, W)
input_batch = input_tensor.unsqueeze(0).to(device)

# 4. Thực hiện dự đoán (Predict)
with torch.no_grad():
    # Đầu ra sẽ có shape: [1, 2, 512, 512]
    output = unet(input_batch)
    
    # Dùng argmax theo chiều channel (dim=1) để lấy index của class có xác suất cao nhất (0 hoặc 1)
    predicted_mask = torch.argmax(output, dim=1) # Shape mới: [1, 512, 512]

# 5. Hiển thị kết quả
# Ép kiểu về numpy array để vẽ bằng matplotlib
mask_to_show = predicted_mask.squeeze().cpu().numpy() # Bỏ batch dimension, còn [512, 512]
image_to_show = image.resize((512, 512))
print(f"Thời gian thực hiện dự đoán: {time.time() - start_time:.2f} giây")
plt.figure(figsize=(12, 6))

# Ảnh X-quang gốc đã resize
plt.subplot(1, 2, 1)
plt.title("Ảnh X-quang gốc (512x512)")
plt.imshow(image_to_show, cmap='gray')
plt.axis('off')

# Mask vùng phổi dự đoán
plt.subplot(1, 2, 2)
plt.title("Vùng phổi dự đoán (Segmentation Mask)")
# Dùng cmap='magma' hoặc 'jet' để phần mask nổi bật lên trên nền đen
plt.imshow(mask_to_show, cmap='magma') 
plt.axis('off')

plt.tight_layout()
plt.show()
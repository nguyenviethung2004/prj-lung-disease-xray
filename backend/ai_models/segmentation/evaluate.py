import os
import time
import torch
import numpy as np
from PIL import Image
from torchvision import transforms
from models import ResNet18UNet # Import từ file models.py của bạn

# --- 1. HÀM TÍNH TOÁN METRICS ---
def calculate_metrics(pred_mask, true_mask):
    """
    Tính toán các chỉ số cho bài toán phân vùng nhị phân (Binary Segmentation)
    Input shape: pred_mask, true_mask đều là [H, W] (Tensor hoặc Numpy)
    """
    # Ép kiểu về boolean tensor
    pred = (pred_mask == 1)
    true = (true_mask == 1)

    TP = (pred & true).sum().float() # True Positive: Dự đoán phổi, thực tế là phổi
    FP = (pred & ~true).sum().float() # False Positive: Dự đoán phổi, thực tế là nền
    FN = (~pred & true).sum().float() # False Negative: Dự đoán nền, thực tế là phổi
    TN = (~pred & ~true).sum().float() # True Negative: Dự đoán nền, thực tế là nền

    epsilon = 1e-6 # Tránh chia cho 0

    iou = TP / (TP + FP + FN + epsilon)
    dice = (2 * TP) / (2 * TP + FP + FN + epsilon)
    accuracy = (TP + TN) / (TP + TN + FP + FN + epsilon)
    precision = TP / (TP + FP + epsilon)
    recall = TP / (TP + FN + epsilon) # Còn gọi là Sensitivity

    return iou.item(), dice.item(), accuracy.item(), precision.item(), recall.item()

# --- 2. KHỞI TẠO ---
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Đang sử dụng thiết bị: {device}")

unet = ResNet18UNet(out_channels=2) 
model_name = "model-ai/segmentation/unet_resnet18/unet_resnet18.pt"

unet.load_state_dict(torch.load(model_name, map_location=device))
unet.to(device)
unet.eval()

# --- 3. ĐƯỜNG DẪN FOLDER ---
# THAY ĐỔI ĐƯỜNG DẪN THƯ MỤC CỦA BẠN TẠI ĐÂY
image_folder = r"./dataset/ChestXray/test/image"
mask_folder = r"./dataset/ChestXray/test/mask"

preprocess_image = transforms.Compose([
    transforms.Resize((512, 512)),
    transforms.ToTensor(), 
])

preprocess_mask = transforms.Compose([
    transforms.Resize((512, 512), interpolation=Image.NEAREST), # Dùng NEAREST cho mask để không bị mờ viền
    transforms.ToTensor(),
])

# Khởi tạo các biến để cộng dồn điểm số
total_iou, total_dice, total_acc, total_prec, total_rec = 0, 0, 0, 0, 0
valid_images_count = 0

image_files = [f for f in os.listdir(image_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]
total_images = len(image_files)

print(f"Bắt đầu đánh giá trên {total_images} ảnh...")
start_time = time.time()

# --- 4. LẶP QUA TỪNG ẢNH ĐỂ ĐÁNH GIÁ ---
with torch.no_grad():
    for img_name in image_files:
        img_path = os.path.join(image_folder, img_name)
        mask_name = img_name.replace("cxrimage_", "cxrmask_")
        mask_name = os.path.splitext(mask_name)[0] + ".jpeg"
        mask_path = os.path.join(mask_folder, mask_name) 

        if not os.path.exists(mask_path):
            print(f"Cảnh báo: Không tìm thấy mask cho ảnh {img_name}, bỏ qua...")
            continue

        # Đọc ảnh gốc (1 channel)
        image = Image.open(img_path).convert("L")
        input_tensor = preprocess_image(image).unsqueeze(0).to(device)

        # Đọc mask chuẩn (1 channel)
        true_mask_img = Image.open(mask_path).convert("L")
        # Chuyển mask về tensor, và nhị phân hóa (nhỏ hơn 0.5 là 0, lớn hơn 0.5 là 1)
        true_mask_tensor = preprocess_mask(true_mask_img).squeeze(0).to(device)
        true_mask_binary = (true_mask_tensor > 0.5).long()

        # Dự đoán
        output = unet(input_tensor)
        predicted_mask = torch.argmax(output, dim=1).squeeze(0) # Shape: [512, 512]

        # Tính metrics cho ảnh hiện tại
        iou, dice, acc, prec, rec = calculate_metrics(predicted_mask, true_mask_binary)

        # Cộng dồn
        total_iou += iou
        total_dice += dice
        total_acc += acc
        total_prec += prec
        total_rec += rec
        valid_images_count += 1

# --- 5. TỔNG HỢP VÀ IN KẾT QUẢ ---
if valid_images_count > 0:
    avg_iou = total_iou / valid_images_count
    avg_dice = total_dice / valid_images_count
    avg_acc = total_acc / valid_images_count
    avg_prec = total_prec / valid_images_count
    avg_rec = total_rec / valid_images_count

    print("-" * 30)
    print("KẾT QUẢ ĐÁNH GIÁ (AVERAGE METRICS):")
    print(f"Tổng số ảnh hợp lệ đã đánh giá: {valid_images_count}")
    print(f"Tổng thời gian: {time.time() - start_time:.2f} giây")
    print(f"IoU (Jaccard Index): {avg_iou:.4f}")
    print(f"Dice Coefficient (F1): {avg_dice:.4f}")
    print(f"Accuracy:            {avg_acc:.4f}")
    print(f"Precision:           {avg_prec:.4f}")
    print(f"Recall (Sensitivity):{avg_rec:.4f}")
    print("-" * 30)
else:
    print("Không có ảnh nào được đánh giá. Vui lòng kiểm tra lại đường dẫn thư mục image và mask.")
import os
import torch
from PIL import Image
from torch.utils.data import Dataset, DataLoader, random_split, Subset
from torchvision import transforms
from sklearn.model_selection import train_test_split
import pickle
from tqdm import tqdm # Thêm thư viện hiển thị thanh tiến trình
from sklearn.metrics import classification_report, confusion_matrix # Thêm thư viện đánh giá
from data_processing import RawXrayTransforms, DatasetWrapper, RawXrayDataset, RawXrayDataModule
# --- BẠN GIỮ NGUYÊN CÁC CLASS BÊN TRÊN CỦA BẠN Ở ĐÂY ---
# (RawXrayTransforms, DatasetWrapper, RawXrayDataset, RawXrayDataModule)

# Import mô hình của bạn
from models import RSNADenseNet121, RSNAResNet50

if __name__ == "__main__":
    # 1. Cấu hình đường dẫn (Sử dụng đúng đường dẫn file PKL bạn đã cung cấp)
    DATA_DIR = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_classification_dataset\rsna_cropped_images"
    SPLIT_FILE = r"D:\doan\backend\prj-lung-disease-xray\model-ai\classification\model_best\3_class\crop\resnet\data_split_by_name.pkl"
    MODEL_PATH = r"D:\doan\backend\prj-lung-disease-xray\model-ai\classification\model_best\3_class\crop\resnet\resnet_224_epoch_11.pth"

    # Kích thước ảnh cho DenseNet121 thường là 224 (bạn có thể đổi nếu lúc train dùng size khác)
    IMAGE_SIZE = 224
    BATCH_SIZE = 32
    NUM_CLASSES = 3

    # 2. Khởi tạo DataModule và lấy Test Loader
    print("--- CHUẨN BỊ DỮ LIỆU ---")
    data_module = RawXrayDataModule(
        data_dir=DATA_DIR, 
        batch_size=BATCH_SIZE, 
        image_size=IMAGE_SIZE, 
        split_file=SPLIT_FILE
    )
    data_module.setup()
    test_loader = data_module.get_test_loader()

    # 3. Khởi tạo và nạp mô hình
    print("\n--- TẢI MÔ HÌNH ---")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Đang sử dụng thiết bị: {device}")
    
    # Khởi tạo kiến trúc mô hình (Cần truyền đúng số class nếu file models.py của bạn yêu cầu)
    model = RSNAResNet50(num_classes=NUM_CLASSES)
    
    # Tải checkpoint
    checkpoint = torch.load(MODEL_PATH, map_location=device)
    
    # Xử lý các cách lưu checkpoint khác nhau
    if 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
        print(f"Đã tải mô hình từ epoch {checkpoint.get('epoch', 'Không rõ')}")
    elif 'state_dict' in checkpoint:
        model.load_state_dict(checkpoint['state_dict'])
    else:
        # Trường hợp lưu trực tiếp model.state_dict()
        model.load_state_dict(checkpoint)
        
    model.to(device)
    model.eval() # Cực kỳ quan trọng: chuyển sang chế độ suy luận (tắt Dropout, BatchNorm)

    # 4. Tiến hành đánh giá (Evaluation) trên tập Test
    print("\n--- BẮT ĐẦU ĐÁNH GIÁ TRÊN TẬP TEST ---")
    all_preds = []
    all_labels = []
    
    # Sử dụng torch.no_grad() để tiết kiệm bộ nhớ và tăng tốc độ vì không cần tính đạo hàm
    with torch.no_grad():
        for images, labels in tqdm(test_loader, desc="Đang dự đoán"):
            images = images.to(device)
            labels = labels.to(device)
            
            outputs = model(images)
            
            # Lấy class có xác suất cao nhất
            _, preds = torch.max(outputs, 1)
            
            # Lưu lại kết quả để tính toán metrics
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    # 5. In báo cáo kết quả
    print("\n--- KẾT QUẢ ĐÁNH GIÁ (CLASSIFICATION REPORT) ---")
    target_names = ['Class 0', 'Class 1', 'Class 2'] # Tên các nhãn của bạn
    report = classification_report(all_labels, all_preds, target_names=target_names, digits=4)
    print(report)

    print("\n--- MA TRẬN NHẦM LẪN (CONFUSION MATRIX) ---")
    cm = confusion_matrix(all_labels, all_preds)
    print(cm)
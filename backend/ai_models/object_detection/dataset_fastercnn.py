import os
import torch
from PIL import Image
from torch.utils.data import Dataset
import torchvision.transforms.functional as F

class XRayDataset(Dataset):
    def __init__(self, image_dir, label_dir):
        """
        Đọc dữ liệu ảnh và nhãn (.txt) đã được chuẩn bị sẵn.
        Args:
            image_dir (str): Thư mục chứa ảnh (VD: 'data/images/train')
            label_dir (str): Thư mục chứa nhãn (VD: 'data/labels/train')
        """
        self.image_dir = image_dir
        self.label_dir = label_dir
        
        # Quét toàn bộ file ảnh hợp lệ trong thư mục
        valid_extensions = ('.jpg', '.png', '.jpeg')
        self.image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(valid_extensions)]

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, idx):
        # ==========================================
        # 1. ĐỌC VÀ CHUẨN HÓA ẢNH
        # ==========================================
        img_name = self.image_files[idx]
        img_path = os.path.join(self.image_dir, img_name)
        
        # Mở ảnh bằng PIL và ép về hệ màu RGB (3 kênh)
        image = Image.open(img_path).convert("RGB")
        img_width, img_height = image.size

        # Chuyển ảnh thành Tensor [C, H, W] và chuẩn hóa giá trị pixel về [0.0, 1.0]
        image_tensor = F.to_tensor(image)

        # ==========================================
        # 2. ĐỌC VÀ CHUYỂN ĐỔI TỌA ĐỘ NHÃN (.TXT)
        # ==========================================
        label_name = os.path.splitext(img_name)[0] + ".txt"
        label_path = os.path.join(self.label_dir, label_name)

        boxes = []
        labels = []
        areas = []

        # Kiểm tra file txt có tồn tại và không bị rỗng
        if os.path.exists(label_path) and os.path.getsize(label_path) > 0:
            with open(label_path, 'r') as f:
                lines = f.readlines()
                
            for line in lines:
                parts = line.strip().split()
                if len(parts) != 5:
                    continue # Bỏ qua nếu dòng bị lỗi format
                
                # Cấu trúc gốc: [class_id, x_center, y_center, width, height] (tỷ lệ 0-1)
                # Cấu trúc đã convert: [class_id, xmin, ymin, xmax, ymax] (Pixel tuyệt đối)
                class_id = int(parts[0])
                xmin = float(parts[1])
                ymin = float(parts[2])
                xmax = float(parts[3])
                ymax = float(parts[4])

                # Tính lại width và height để lưu vào biến area (bắt buộc cho Faster R-CNN)
                w = xmax - xmin
                h = ymax - ymin

                boxes.append([xmin, ymin, xmax, ymax])
                
                # QUAN TRỌNG: Faster R-CNN tính Background là 0, nên bệnh phải là 1
                labels.append(class_id + 1) 
                areas.append(w * h)

        # ==========================================
        # 3. ĐÓNG GÓI THÀNH TENSOR ĐÚNG CHUẨN
        # ==========================================
        if len(boxes) > 0:
            boxes = torch.tensor(boxes, dtype=torch.float32)
            labels = torch.tensor(labels, dtype=torch.int64)
            areas = torch.tensor(areas, dtype=torch.float32)
        else:
            # Xử lý các ảnh KHÔNG CÓ BỆNH (Ảnh nền khỏe mạnh)
            boxes = torch.zeros((0, 4), dtype=torch.float32)
            labels = torch.zeros((0,), dtype=torch.int64)
            areas = torch.zeros((0,), dtype=torch.float32)

        iscrowd = torch.zeros((labels.shape[0],), dtype=torch.int64)

        # Tạo Dictionary Target bắt buộc
        target = {}
        target["boxes"] = boxes
        target["labels"] = labels
        target["image_id"] = torch.tensor([idx])
        target["area"] = areas
        target["iscrowd"] = iscrowd

        return image_tensor, target
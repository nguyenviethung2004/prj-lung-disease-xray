import os
import torch
from PIL import Image
from torch.utils.data import Dataset, DataLoader, random_split, Subset
from torchvision import transforms
from sklearn.model_selection import train_test_split
import pickle
# ==========================================
# CLASS 1: QUẢN LÝ DATA AUGMENTATION
# ==========================================
class RawXrayTransforms:
    """Class định nghĩa các phép biến đổi ảnh đầu vào. Kích thước sẽ phụ thuộc vào Model."""
    def __init__(self, image_size):
        self.image_size = image_size
        # Mean và Std chuẩn của ImageNet
        self.mean = [0.485, 0.456, 0.406]
        self.std = [0.229, 0.224, 0.225]

    def get_train_transforms(self):
        return transforms.Compose([
            transforms.Resize((self.image_size, self.image_size)),
            transforms.RandomRotation(degrees=10),
            transforms.RandomHorizontalFlip(p=0.3),
            transforms.ToTensor(),
            transforms.Normalize(mean=self.mean, std=self.std)
        ])

    def get_val_transforms(self):
        # Tập Validation/Test KHÔNG được augment, chỉ resize và chuẩn hóa
        return transforms.Compose([
            transforms.Resize((self.image_size, self.image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=self.mean, std=self.std)
        ])

# ==========================================
# CLASS WRAPPER: GIẢI QUYẾT LỖI RANDOM_SPLIT CỦA PYTORCH
# ==========================================
class DatasetWrapper(Dataset):
    """Lớp bọc để áp dụng Transform riêng biệt cho Train và Val sau khi chia cắt"""
    def __init__(self, subset, transform=None):
        self.subset = subset
        self.transform = transform

    def __getitem__(self, index):
        image, label = self.subset[index]
        if self.transform:
            image = self.transform(image)
        return image, label

    def __len__(self):
        return len(self.subset)

# ==========================================
# CLASS 2: QUẢN LÝ DATASET ĐỌC TỪ FOLDER
# ==========================================
class RawXrayDataset(Dataset):
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.image_paths = []
        self.labels = []
        # Thêm một list để lưu tên file duy nhất (ID)
        self.filenames = [] 
        self.classes = ['0', '1', '2']
        self._load_image_paths()

    def _load_image_paths(self):
        for class_label in self.classes:
            class_dir = os.path.join(self.root_dir, class_label)
            if not os.path.exists(class_dir): continue
            for file_name in os.listdir(class_dir):
                if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    full_path = os.path.join(class_dir, file_name)
                    self.image_paths.append(full_path)
                    self.labels.append(int(class_label))
                    # Lưu tên file làm ID (ví dụ: "patient_001.jpg")
                    self.filenames.append(file_name) 

    def __len__(self): 
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        image = Image.open(self.image_paths[idx]).convert('RGB')
        return image, torch.tensor(self.labels[idx], dtype=torch.long)

# ==========================================
# CLASS 3: DATA MODULE (QUẢN LÝ LUỒNG DATALOADER)
# ==========================================
class RawXrayDataModule:
    def __init__(self, data_dir, batch_size=32, val_split=0.15, test_split=0.15, 
                 image_size=224, split_file="data_split_by_name.pkl"):
        self.data_dir = data_dir
        self.batch_size = batch_size
        self.val_split = val_split
        self.test_split = test_split
        self.image_size = image_size
        self.split_file = split_file
        self.transforms = RawXrayTransforms(image_size=self.image_size)

    def setup(self):
        full_dataset = RawXrayDataset(self.data_dir)
        
        if os.path.exists(self.split_file):
            print(f"Đang tải danh sách tên file từ: {self.split_file}")
            with open(self.split_file, 'rb') as f:
                split_names = pickle.load(f)
            
            # Ánh xạ ngược từ Tên file -> Index hiện tại trong Dataset
            name_to_idx = {name: i for i, name in enumerate(full_dataset.filenames)}
            
            # Lấy ra index tương ứng với các tên file đã lưu
            train_idx = [name_to_idx[n] for n in split_names['train'] if n in name_to_idx]
            val_idx = [name_to_idx[n] for n in split_names['val'] if n in name_to_idx]
            test_idx = [name_to_idx[n] for n in split_names['test'] if n in name_to_idx]
            
        else:
            print("✂️ Đang chia dữ liệu mới bằng tên file...")
            indices = list(range(len(full_dataset)))
            
            # Chia index trước để tận dụng Stratify (cân bằng nhãn)
            train_val_idx, test_idx = train_test_split(
                indices, test_size=self.test_split, random_state=42, stratify=full_dataset.labels
            )
            relative_val_size = self.val_split / (1 - self.test_split)
            train_idx, val_idx = train_test_split(
                train_val_idx, test_size=relative_val_size, random_state=42, 
                stratify=[full_dataset.labels[i] for i in train_val_idx]
            )

            # Chuyển đổi từ Index sang Tên file để lưu vào PKL
            split_names = {
                'train': [full_dataset.filenames[i] for i in train_idx],
                'val':   [full_dataset.filenames[i] for i in val_idx],
                'test':  [full_dataset.filenames[i] for i in test_idx]
            }
            
            with open(self.split_file, 'wb') as f:
                pickle.dump(split_names, f)
            print(f"💾 Đã lưu danh sách tên file vào: {self.split_file}")

        # Tạo Subset dựa trên Index đã ánh xạ
        self.train_dataset = DatasetWrapper(Subset(full_dataset, train_idx), transform=self.transforms.get_train_transforms())
        self.val_dataset = DatasetWrapper(Subset(full_dataset, val_idx), transform=self.transforms.get_val_transforms())
        self.test_dataset = DatasetWrapper(Subset(full_dataset, test_idx), transform=self.transforms.get_val_transforms())

        print(f"✅ Khởi tạo xong! Train: {len(train_idx)} | Val: {len(val_idx)} | Test: {len(test_idx)}")

    def get_train_loader(self):
        return DataLoader(self.train_dataset, batch_size=self.batch_size, shuffle=True, num_workers=4, pin_memory=True)

    def get_val_loader(self):
        return DataLoader(self.val_dataset, batch_size=self.batch_size, shuffle=False, num_workers=4, pin_memory=True)

    def get_test_loader(self):
        return DataLoader(self.test_dataset, batch_size=self.batch_size, shuffle=False, num_workers=4, pin_memory=True)



if __name__ == "__main__":
    DATA_DIR = r"D:\doan\backend\prj-lung-disease-xray\dataset\rsna_classification_dataset"
    
    # Khởi tạo cho EfficientNet-B4 (ví dụ)
    data_module = RawXrayDataModule(data_dir=DATA_DIR, batch_size=16, image_size=380, split_file="rsna_split.pkl")
    data_module.setup()
    
    # Kiểm tra loader
    test_loader = data_module.get_test_loader()
    print(f"Số lượng batch trong tập Test: {len(test_loader)}")
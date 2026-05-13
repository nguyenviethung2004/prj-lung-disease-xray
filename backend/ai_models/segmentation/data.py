import random
import os
import shutil
import torch
import torchvision
import numpy as np
import torchvision.transforms.functional as F
from PIL import Image

from pathlib import Path

def find_file(folder, file_name):
    files = list(folder.glob(file_name + ".*"))
    if len(files) == 0:
        raise FileNotFoundError(f"Không tìm thấy file: {file_name} trong {folder}")
    return files[0]

class LungDataset(torch.utils.data.Dataset):
    def __init__(self, origin_mask_list, origins_folder, masks_folder, transforms=None):
        self.origin_mask_list = origin_mask_list
        self.origins_folder = origins_folder
        self.masks_folder = masks_folder
        self.transforms = transforms
    
    def __getitem__(self, idx):
        file_name = self.origin_mask_list[idx]
        origin_name = file_name.replace("cxrmask_", "cxrimage_")
        origin_path = find_file(self.origins_folder, origin_name)
        mask_path = find_file(self.masks_folder, file_name)

        origin = Image.open(origin_path).convert("L")
        mask = Image.open(mask_path).convert("L")
        if self.transforms is not None:
            origin, mask = self.transforms((origin, mask))
            
        origin = torchvision.transforms.functional.to_tensor(origin) - 0.5
    
        mask = np.array(mask)
        mask = (torch.tensor(mask) > 128).long() 
        return origin, mask
        
    
    def __len__(self):
        return len(self.origin_mask_list)

    
class Pad():
    def __init__(self, max_padding):
        self.max_padding = max_padding
        
    def __call__(self, sample):
        origin, mask = sample
        padding = np.random.randint(0, self.max_padding)
#         origin = torchvision.transforms.functional.pad(origin, padding=padding, padding_mode="symmetric")
        origin = torchvision.transforms.functional.pad(origin, padding=padding, fill=0)
        mask = torchvision.transforms.functional.pad(mask, padding=padding, fill=0)
        return origin, mask


class Crop():
    def __init__(self, max_shift):
        self.max_shift = max_shift
        
    def __call__(self, sample):
        origin, mask = sample
        origin_w, origin_h = origin.size
        
        # 1. Giới hạn max_shift không được vượt quá 1/4 kích thước ảnh
        # (Để tl_shift + br_shift tối đa chỉ mất 1/2 ảnh, vẫn còn 1/2 để AI nhìn)
        safe_limit_w = min(self.max_shift, origin_w // 4)
        safe_limit_h = min(self.max_shift, origin_h // 4)
        
        # 2. Random ngẫu nhiên trong khoảng an toàn
        tl_shift_w = np.random.randint(0, safe_limit_w) if safe_limit_w > 0 else 0
        tl_shift_h = np.random.randint(0, safe_limit_h) if safe_limit_h > 0 else 0
        br_shift_w = np.random.randint(0, safe_limit_w) if safe_limit_w > 0 else 0
        br_shift_h = np.random.randint(0, safe_limit_h) if safe_limit_h > 0 else 0
        
        # 3. Tính toán kích thước sau khi crop (Luôn dương)
        crop_w = origin_w - tl_shift_w - br_shift_w
        crop_h = origin_h - tl_shift_h - br_shift_h
        
        # 4. Thực hiện Crop
        origin = torchvision.transforms.functional.crop(origin, tl_shift_h, tl_shift_w,
                                                        crop_h, crop_w)
        mask = torchvision.transforms.functional.crop(mask, tl_shift_h, tl_shift_w,
                                                        crop_h, crop_w)
        return origin, mask


class Resize():
    def __init__(self, output_size):
        self.output_size = output_size
        
    def __call__(self, sample):
        origin, mask = sample
        origin = torchvision.transforms.functional.resize(origin, self.output_size)
        mask = torchvision.transforms.functional.resize(mask, self.output_size)
        
        return origin, mask

    
class RandomHorizontalFlip():
    """Lật ngang ngẫu nhiên cả ảnh và mask (Xác suất p)"""
    def __init__(self, p=0.5):
        self.p = p
        
    def __call__(self, sample):
        origin, mask = sample
        if random.random() < self.p:
            origin = F.hflip(origin)
            mask = F.hflip(mask)
        return origin, mask

class RandomRotation():
    """Xoay nghiêng ngẫu nhiên một góc nhỏ cho cả ảnh và mask"""
    def __init__(self, degrees=10, p=0.5):
        self.degrees = degrees
        self.p = p
        
    def __call__(self, sample):
        origin, mask = sample
        if random.random() < self.p:
            angle = random.uniform(-self.degrees, self.degrees)
            # Dùng interpolation mặc định (Nearest) để mask không bị nhòe giá trị
            origin = F.rotate(origin, angle)
            mask = F.rotate(mask, angle)
        return origin, mask


class RandomBrightness():
    """Chỉnh độ sáng ngẫu nhiên (CHỈ ÁP DỤNG CHO ẢNH GỐC, GIỮ NGUYÊN MASK)"""
    def __init__(self, brightness_factor=0.2, p=0.5):
        self.brightness_factor = brightness_factor
        self.p = p
        
    def __call__(self, sample):
        origin, mask = sample
        if random.random() < self.p:
            # Random hệ số sáng từ (1 - factor) đến (1 + factor)
            factor = 1.0 + random.uniform(-self.brightness_factor, self.brightness_factor)
            origin = F.adjust_brightness(origin, factor)
            # Mask không thay đổi
        return origin, mask


def blend(origin, mask1=None, mask2=None):
    img = torchvision.transforms.functional.to_pil_image(origin + 0.5).convert("RGB")
    if mask1 is not None:
        mask1 =  torchvision.transforms.functional.to_pil_image(torch.cat([
            torch.zeros_like(origin),
            torch.stack([mask1.float()]),
            torch.zeros_like(origin)
        ]))
        img = Image.blend(img, mask1, 0.2)
        
    if mask2 is not None:
        mask2 =  torchvision.transforms.functional.to_pil_image(torch.cat([
            torch.stack([mask2.float()]),
            torch.zeros_like(origin),
            torch.zeros_like(origin)
        ]))
        img = Image.blend(img, mask2, 0.2)
    
    return img




def move_images(input_folder, output_folder):
    """
    Chuyển các file ảnh từ input_folder sang output_folder.
    """
    # 1. Kiểm tra nếu thư mục output chưa tồn tại thì tạo mới
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Đã tạo thư mục mới: {output_folder}")

    # 2. Định nghĩa các đuôi file ảnh hợp lệ (có thể thêm bớt tùy ý)
    valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
    
    # Biến đếm số lượng ảnh đã chuyển
    count = 0 

    # 3. Duyệt qua tất cả các file trong thư mục input
    for filename in os.listdir(input_folder):
        # Chuyển tên file về chữ thường để kiểm tra đuôi file chính xác
        if filename.lower().endswith(valid_extensions):
            source_path = os.path.join(input_folder, filename)
            destination_path = os.path.join(output_folder, filename)

            try:
                # 4. Thực hiện di chuyển file
                # Lưu ý: Nếu muốn "Copy" thay vì "Move", hãy đổi shutil.move thành shutil.copy
                shutil.move(source_path, destination_path)
                print(f"Đã chuyển: {filename}")
                count += 1
            except Exception as e:
                print(f"Lỗi khi chuyển file {filename}: {e}")

    print(f"\n=> Hoàn thành! Đã chuyển tổng cộng {count} file ảnh.")


def move_extra_images(img_folder, mask_folder, extra_folder):
    """
    Lọc và di chuyển các ảnh thừa từ img_folder sang extra_folder 
    dựa trên danh sách ảnh chuẩn ở mask_folder.
    """
    # 1. Tạo thư mục chứa ảnh thừa nếu chưa tồn tại
    if not os.path.exists(extra_folder):
        os.makedirs(extra_folder)
        print(f"Đã tạo thư mục chứa ảnh thừa: {extra_folder}")

    # 2. Lấy danh sách tên file trong thư mục mask 
    # Dùng kiểu dữ liệu 'set' để việc tìm kiếm (so sánh) diễn ra cực kỳ nhanh
    mask_files = set(f for f in os.listdir(mask_folder) if os.path.isfile(os.path.join(mask_folder, f)))
    
    count = 0
    extra_list = []

    # 3. Duyệt qua tất cả các file trong thư mục img
    for filename in os.listdir(img_folder):
        img_path = os.path.join(img_folder, filename)
        
        # Bỏ qua nếu đó là thư mục con, chỉ xử lý file
        if os.path.isfile(img_path):
            # 4. Nếu tên ảnh KHÔNG CÓ trong danh sách mask_files -> Đây là ảnh thừa
            if filename not in mask_files:
                extra_list.append(filename)
                
                destination_path = os.path.join(extra_folder, filename)
                
                try:
                    # Di chuyển ảnh thừa ra khỏi thư mục img
                    shutil.move(img_path, destination_path)
                    print(f"Đã chuyển ảnh thừa: {filename}")
                    count += 1
                except Exception as e:
                    print(f"Lỗi khi chuyển file {filename}: {e}")

    print(f"\n=> Hoàn thành! Đã tìm thấy và chuyển đi {count} ảnh thừa.")
    print(f"Hiện tại thư mục gốc '{img_folder}' chỉ còn lại các ảnh khớp với '{mask_folder}'.")
    
    return extra_list


def rename_remove_mask(folder_path):
    """
    Duyệt qua các file trong thư mục và đổi tên bằng cách xóa '_mask' khỏi tên file.
    """
    # 1. Kiểm tra xem thư mục có tồn tại không
    if not os.path.exists(folder_path):
        print(f"Lỗi: Thư mục '{folder_path}' không tồn tại!")
        return

    count = 0

    # 2. Duyệt qua tất cả các file trong thư mục
    for filename in os.listdir(folder_path):
        # Chỉ xử lý những file có chứa chuỗi '_mask' trong tên
        if "_mask" in filename:
            # 3. Tạo tên file mới bằng cách thay thế '_mask' thành chuỗi rỗng
            new_filename = filename.replace("_mask", "")
            
            # 4. Tạo đường dẫn đầy đủ cho file cũ và file mới
            old_file_path = os.path.join(folder_path, filename)
            new_file_path = os.path.join(folder_path, new_filename)
            
            try:
                # 5. Thực hiện đổi tên file
                os.rename(old_file_path, new_file_path)
                print(f"Đã đổi: {filename}  -->  {new_filename}")
                count += 1
            except Exception as e:
                print(f"Lỗi khi đổi tên file {filename}: {e}")

    print(f"\n=> Hoàn thành! Đã xử lý đổi tên tổng cộng {count} file.")



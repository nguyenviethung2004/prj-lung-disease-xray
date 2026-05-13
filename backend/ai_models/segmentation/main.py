from datetime import datetime
import os
import glob
import time 
import pickle
import torch
import torchvision
import pandas as pd
import numpy as np
import wandb
from pathlib import Path
from sklearn.model_selection import train_test_split
import wandb
from data import LungDataset, Pad, Crop, Resize, RandomBrightness, RandomHorizontalFlip, RandomRotation
from models import PretrainedUNet
from metrics import jaccard, dice, precision_recall, accuracy_specificity
from config import parse_args
from .logs import log_and_save


def prepare_splits(masks_list, split_file="splits.pk"):
    """Xử lý việc chia tập dữ liệu Train/Val/Test."""
    if os.path.isfile(split_file):
        with open(split_file, "rb") as f:
            splits = pickle.load(f)
            print("Đã tải dữ liệu phân chia từ splits.pk")
    else:
        splits = {}
        # Chia test 20%
        splits["train"], splits["test"] = train_test_split(masks_list, test_size=0.2, random_state=42)
        # Chia val 10% từ tập train
        splits["train"], splits["val"] = train_test_split(splits["train"], test_size=0.1, random_state=42)
        
        with open(split_file, "wb") as f:
            pickle.dump(splits, f)
            print("Đã tạo mới và lưu splits.pk")
            
    return splits

# def create_dataloaders(splits, origins_folder, masks_folder, batch_size=4):
#     """Tạo các Dataloader cho Train, Val và Test."""
#     val_test_transforms = torchvision.transforms.Compose([
#         Resize((512, 512)),
#     ])
    
#     train_transforms = torchvision.transforms.Compose([
#         Pad(200),
#         RandomRotation(degrees=10, p=0.5),     # 1. Xoay ngẫu nhiên
#         RandomHorizontalFlip(p=0.5),           # 2. Lật ngang ngẫu nhiên
#         Crop(300),
#         RandomBrightness(brightness_factor=0.2, p=0.5), # 3. Chỉnh sáng ngẫu nhiên
#         val_test_transforms,                   # Cuối cùng mới Resize về 512x512
#     ])

#     datasets = {
#         x: LungDataset(
#             splits[x], 
#             origins_folder, 
#             masks_folder, 
#             train_transforms if x == "train" else val_test_transforms
#         ) for x in ["train", "test", "val"]
#     }

#     dataloaders = {
#         x: torch.utils.data.DataLoader(datasets[x], batch_size=batch_size, shuffle=(x=="train")) 
#         for x in ["train", "test", "val"]
#     }
    
#     return datasets, dataloaders

def create_dataloaders(data_folder, batch_size=4):
    """Tạo các Dataloader bằng cách đọc trực tiếp từ các thư mục con train/val/test."""
    val_test_transforms = torchvision.transforms.Compose([
        Resize((512, 512)),
    ])
    
    train_transforms = torchvision.transforms.Compose([
        Pad(30),
        RandomRotation(degrees=10, p=0.5),
        RandomHorizontalFlip(p=0.5),
        Crop(50),
        RandomBrightness(brightness_factor=0.2, p=0.5),
        val_test_transforms,
    ])

    datasets = {}
    dataloaders = {}
    
    # Lặp qua 3 thư mục đã chia sẵn
    for phase in ["train", "val", "test"]:
        phase_dir = Path(data_folder) / phase
        origins_folder = phase_dir / "image"
        masks_folder = phase_dir / "mask"
        
        # Lấy danh sách tên file từ thư mục masks
        file_names = [f.stem for f in masks_folder.glob("*.png")]
        
        datasets[phase] = LungDataset(
            file_names, 
            origins_folder, 
            masks_folder, 
            train_transforms if phase == "train" else val_test_transforms
        )
        
        dataloaders[phase] = torch.utils.data.DataLoader(
            datasets[phase], 
            batch_size=batch_size, 
            shuffle=(phase == "train") # Chỉ trộn cho tập train
        )
        print(f"Đã tải {len(file_names)} ảnh cho tập {phase.upper()}")
        
    return datasets, dataloaders

def train_epoch(model, dataloader, optimizer, dataset_size, device):
    """Thực hiện huấn luyện mô hình cho 1 Epoch và tính Loss, Jaccard, Dice."""
    model.train()
    running_loss = 0.0
    running_jaccard = 0.0
    running_dice = 0.0
    
    for origins, masks in dataloader:
        num = origins.size(0)
        origins = origins.to(device)
        masks = masks.to(device)
        
        optimizer.zero_grad()
        
        outs = model(origins)
        softmax = torch.nn.functional.log_softmax(outs, dim=1)
        loss = torch.nn.functional.nll_loss(softmax, masks)
        
        loss.backward()
        optimizer.step()
        
        running_loss += loss.item() * num
        
        # --- THÊM MỚI: Tính Jaccard và Dice cho tập Train ---
        # Dùng torch.no_grad() ở đây để không lưu lịch sử đạo hàm, tiết kiệm RAM
        with torch.no_grad():
            preds = torch.argmax(softmax, dim=1).float()
            masks_float = masks.float()
            running_jaccard += jaccard(masks_float, preds).item() * num
            running_dice += dice(masks_float, preds).item() * num
            
        print(".", end="", flush=True)
        
    print()
    # Trả về 3 giá trị thay vì chỉ 1 như trước
    return (running_loss / dataset_size, 
            running_jaccard / dataset_size, 
            running_dice / dataset_size)

def validate_epoch(model, dataloader, dataset_size, device):
    """Thực hiện đánh giá mô hình với ĐẦY ĐỦ các chỉ số."""
    model.eval()
    val_loss, val_jaccard, val_dice = 0.0, 0.0, 0.0
    val_acc, val_prec, val_rec, val_spec = 0.0, 0.0, 0.0, 0.0

    with torch.no_grad():
        for origins, masks in dataloader:
            num = origins.size(0)
            origins = origins.to(device)
            masks = masks.to(device)

            outs = model(origins)
            softmax = torch.nn.functional.log_softmax(outs, dim=1)
            loss = torch.nn.functional.nll_loss(softmax, masks).item()
            
            preds = torch.argmax(softmax, dim=1).float()
            masks_float = masks.float()
            
            # Tính các chỉ số
            prec, rec = precision_recall(masks_float, preds)
            acc, spec = accuracy_specificity(masks_float, preds)
            
            # Cộng dồn
            val_loss += loss * num
            val_jaccard += jaccard(masks_float, preds).item() * num
            val_dice += dice(masks_float, preds).item() * num
            
            val_acc += acc.item() * num
            val_prec += prec.item() * num
            val_rec += rec.item() * num
            val_spec += spec.item() * num

            print(".", end="", flush=True)
            
    print()        
    return (val_loss / dataset_size, 
            val_jaccard / dataset_size, 
            val_dice / dataset_size,
            val_acc / dataset_size,
            val_prec / dataset_size,
            val_rec / dataset_size,
            val_spec / dataset_size)



def main():
    args = parse_args() # 1. Phân tích tham số từ dòng lệnh
    results_folder = Path(args.results_dir)
    results_folder.mkdir(parents=True, exist_ok=True) 
    # Khởi tạo Weights & Biases nếu người dùng bật cờ --is_wandb
    if args.is_wandb:
        # Tự động lấy tên version từ args kết hợp với thời gian thực (như đã làm ở bước trước)
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_name = f"{getattr(args, 'version', 'v1.0')}_{args.model_name}_{current_time}"
        
        wandb.init(
            project="unet-segmentation", 
            name=run_name, 
            config=vars(args),
            dir=str(results_folder) 
        )

    # 1. Cấu hình thiết bị và đường dẫn
    if args.device == "cuda" and not torch.cuda.is_available():
        print("Cảnh báo: Bạn chọn cuda nhưng máy không có GPU. Chuyển về dùng CPU.")
        device = torch.device("cpu")
    else:
        device = torch.device(args.device)

    print(f"Sử dụng thiết bị: {device}")
    data_folder = Path(args.data_dir)
    


    datasets, dataloaders = create_dataloaders(data_folder, batch_size=args.batch_size)
    
    # 3. Khởi tạo mô hình và Optimizer
    unet = PretrainedUNet(in_channels=1, out_channels=2, batch_norm=True, upscale_mode="bilinear")
    unet = unet.to(device)
    optimizer = torch.optim.Adam(unet.parameters(), lr=args.lr)
    
    # 4. Cấu hình quá trình huấn luyện
    epochs = args.epochs
    best_val_loss = np.inf
    
    # Đường dẫn lưu file hoàn chỉnh
    model_save_path = results_folder / args.model_name
    log_file_path = results_folder / args.log_file

    # 5. Vòng lặp huấn luyện chính (Training Loop)
    for e in range(1, epochs + 1):
        print(f"\n{'-'*15} Bắt đầu Epoch {e}/{epochs} {'-'*15}")
        start_t = time.time()
        
        # --- Phase 1: Training ---
        print("Đang Train", end="")
        train_loss, train_jaccard, train_dice = train_epoch(
            unet, dataloaders["train"], optimizer, len(datasets["train"]), device
        )
        
        # --- Phase 2: Validation ---
        print("Đang Validate", end="")
        val_loss, val_jaccard, val_dice, val_accuracy, val_precision, val_recall, val_specificity = validate_epoch(
            unet, dataloaders["val"], len(datasets["val"]), device
        )
        
        # --- Thu thập thông số phụ ---
        time_spent = time.time() - start_t
        current_lr = optimizer.param_groups[0]['lr'] # Lấy Learning Rate thực tế từ Optimizer
        
        # Kiểm tra xem mô hình hiện tại có phải tốt nhất không
        is_best = val_loss < best_val_loss
        if is_best:
            best_val_loss = val_loss
            torch.save(unet.state_dict(), model_save_path) # Lưu ngay vào file
            
        # --- 6. Gọi hàm Log và Save ---
        log_and_save(
            epoch=e, 
            total_epochs=epochs, 
            train_loss=train_loss, 
            train_jaccard=train_jaccard, 
            train_dice=train_dice, 
            val_loss=val_loss, 
            val_jaccard=val_jaccard, 
            val_dice=val_dice, 
            val_accuracy=val_accuracy, 
            val_precision=val_precision, 
            val_recall=val_recall, 
            val_specificity=val_specificity, 
            learning_rate=current_lr, 
            time_spent=time_spent, 
            log_file_path=str(log_file_path), 
            is_best=is_best, 
            is_wandb=args.is_wandb, 
            is_txt=args.is_txt
        )
        
    # Kết thúc quá trình huấn luyện trên wandb (nếu có)
    if args.is_wandb:
        wandb.finish()

if __name__ == "__main__":
    main()
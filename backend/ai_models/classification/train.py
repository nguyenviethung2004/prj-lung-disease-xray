import os
import time
import torch
import torch.nn as nn

# IMPORT từ các file bạn đã viết
from config import parse_args
from data_processing import RawXrayDataModule
from models import RSNAResNet50  # hoặc RSNAEfficientNetB4
from loss import BalancedFocalLoss
from optimizer import RSNAOptimizer
from metrics import classification_metrics
from logs import log_and_save
import wandb
from datetime import datetime
from pathlib import Path

# ==========================
# TRAIN 1 EPOCH
# ==========================
def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()

    total_loss = 0
    all_preds = []
    all_labels = []

    for images, labels in loader:
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()

        outputs = model(images)
        loss = criterion(outputs, labels)

        loss.backward()
        optimizer.step()

        total_loss += loss.item()

        all_preds.append(outputs.detach())
        all_labels.append(labels)

    all_preds = torch.cat(all_preds)
    all_labels = torch.cat(all_labels)

    acc, precision, recall, f1, specificity = classification_metrics(all_labels, all_preds)

    return total_loss / len(loader), acc.item(), precision.item(), recall.item(), f1.item(), specificity.item()

# ==========================
# VALIDATION
# ==========================
def validate(model, loader, criterion, device):
    model.eval()

    total_loss = 0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            loss = criterion(outputs, labels)

            total_loss += loss.item()

            all_preds.append(outputs)
            all_labels.append(labels)

    all_preds = torch.cat(all_preds)
    all_labels = torch.cat(all_labels)

    acc, precision, recall, f1, specificity = classification_metrics(all_labels, all_preds)

    return total_loss / len(loader), acc.item(), precision.item(), recall.item(), f1.item(), specificity.item()

# ==========================
# MAIN TRAIN
# ==========================
def main():
    args = parse_args()
    
    # 1. TẠO THƯ MỤC LƯU TRỮ CHUNG
    # Gom tất cả vào một thư mục cụ thể theo phiên bản: ví dụ "results/v1.0"
    save_dir = Path(args.results_dir) / args.version
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # Ép đường dẫn thành chuỗi (string) để dùng cho các hàm OS/WandB phía dưới
    save_dir_str = str(save_dir)

    # 2. KHỞI TẠO W&B VÀ ÉP LƯU VÀO THƯ MỤC VỪA TẠO
    if args.is_wandb:
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_name = f"{getattr(args, 'version', 'v1.0')}_{args.model_name}_{current_time}"

        wandb.init(
            project="unet-segmentation", # Đổi tên project nếu cần: ví dụ "RSNA_Classification"
            name=run_name,
            config=vars(args),
            # SỬA Ở ĐÂY: Ép WandB lưu thư mục 'wandb' cục bộ vào đúng save_dir
            dir=save_dir_str 
        )

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")

    # ==========================
    # DATA
    # ==========================
    data_module = RawXrayDataModule(
        data_dir=args.data_dir,
        batch_size=args.batch_size,
        image_size=224  # đổi 380 nếu dùng EfficientNet
    )
    data_module.setup()

    train_loader = data_module.get_train_loader()
    val_loader = data_module.get_val_loader()

    # ==========================
    # MODEL
    # ==========================
    model = RSNAResNet50(num_classes=3).to(device)


    train_indices = data_module.train_dataset.subset.indices
    raw_labels = data_module.train_dataset.subset.dataset.labels
    class_counts = [0, 0, 0]
    for idx in train_indices:
        label = raw_labels[idx]
        class_counts[label] += 1

    criterion = BalancedFocalLoss(class_counts=class_counts).to(device)
    print(f"⚖️ Số lượng dữ liệu thực tế dùng để tính Focal Loss (Tập Train): {class_counts}")
    # ==========================
    # OPTIMIZER
    # ==========================
    opt_manager = RSNAOptimizer(model.parameters(), lr=args.lr)
    optimizer = opt_manager.get_optimizer()
    scheduler = opt_manager.get_scheduler()

    # ==========================
    # ĐỊNH NGHĨA ĐƯỜNG DẪN FILE MODEL VÀ LOG 
    # ==========================
    # SỬA Ở ĐÂY: Lưu trực tiếp vào save_dir đã định nghĩa ở trên cùng
    model_path = os.path.join(save_dir_str, args.model_name)
    log_file = os.path.join(save_dir_str, args.log_file)

    best_val_loss = float("inf")

    # ==========================
    # TRAIN LOOP
    # ==========================
    for epoch in range(1, args.epochs + 1):
        start_time = time.time()

        train_loss, train_acc, train_prec, train_rec, train_f1, train_spec = train_one_epoch(
            model, train_loader, criterion, optimizer, device
        )

        val_loss, val_acc, val_prec, val_rec, val_f1, val_spec = validate(
            model, val_loader, criterion, device
        )

        scheduler.step(val_loss)

        epoch_time = time.time() - start_time
        current_lr = optimizer.param_groups[0]['lr']

        is_best = val_loss < best_val_loss
        if is_best:
            best_val_loss = val_loss
            torch.save(model.state_dict(), model_path)

        # LOG
        log_and_save(
            epoch, args.epochs,
            train_loss, train_acc, train_prec, train_rec, train_f1, train_spec,
            val_loss, val_acc, val_prec, val_rec, val_f1, val_spec,
            current_lr, epoch_time,
            log_file, is_best,
            args.is_wandb, args.is_txt
        )

    print(f"Training hoàn tất! Dữ liệu được lưu tại: {save_dir_str}")
    
    if args.is_wandb:
        wandb.finish()

if __name__ == "__main__":
    main()
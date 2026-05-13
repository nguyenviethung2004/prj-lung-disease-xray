import torch
import os
from torch.utils.data import DataLoader
from tqdm import tqdm

# Import các module bạn đã viết
from model_fastercnn import get_faster_rcnn_model
from metrics import MAPEvaluator
from logger import WandbLogger
from config import parse_args
from dataset_fastercnn import XRayDataset # Tích hợp Dataset

def collate_fn(batch):
    """Gom nhóm dữ liệu vì số lượng Bounding Box mỗi ảnh khác nhau"""
    return tuple(zip(*batch))

def main():
    # ==========================================
    # 1. CÀI ĐẶT CƠ BẢN
    # ==========================================
    args = parse_args()
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    os.makedirs(args.project_dir, exist_ok=True)

    print(f"🚀 Thiết bị huấn luyện: {device}")

    # ==========================================
    # 2. KHỞI TẠO MODULE & MÔ HÌNH
    # ==========================================
    logger = WandbLogger(args.project_dir, args.name, vars(args), args.disable_wandb)
    evaluator = MAPEvaluator()
    
    # Số lượng class = 2 (0: Background, 1: Lung_Opacity)
    model = get_faster_rcnn_model(num_classes=2).to(device) 

    # Thuật toán tối ưu (SGD khuyên dùng cho Faster R-CNN)
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(params, lr=args.lr, momentum=0.9, weight_decay=0.0005)
    lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)

    # ==========================================
    # 3. TẢI DỮ LIỆU (DATALOADER)
    # ==========================================
    print("📦 Đang tải dữ liệu...")
    
    train_dataset = XRayDataset(
        image_dir='data/images/train',
        label_dir='data/labels/train'
    )
    
    val_dataset = XRayDataset(
        image_dir='data/images/val',
        label_dir='data/labels/val'
    )

    train_loader = DataLoader(
        train_dataset, 
        batch_size=args.batch_size, 
        shuffle=True, 
        collate_fn=collate_fn, 
        num_workers=4,   # Giúp load ảnh song song nhanh hơn
        pin_memory=True  # Tăng tốc độ chuyển data từ RAM sang GPU
    )
    
    val_loader = DataLoader(
        val_dataset, 
        batch_size=args.batch_size, 
        shuffle=False, 
        collate_fn=collate_fn, 
        num_workers=4,
        pin_memory=True
    )

    # ==========================================
    # 4. VÒNG LẶP HUẤN LUYỆN
    # ==========================================
    print(f"🔥 Bắt đầu huấn luyện phiên bản: {args.name}")
    best_map = 0.0 # Biến theo dõi kỷ lục mAP

    for epoch in range(args.epochs):
        model.train()
        epoch_loss = 0
        
        # --- BƯỚC 1: TRAIN ---
        pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{args.epochs} [Train]")
        for images, targets in pbar:
            # Đẩy ảnh và nhãn lên GPU
            images = list(image.to(device) for image in images)
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

            # Tính Loss
            loss_dict = model(images, targets)
            losses = sum(loss for loss in loss_dict.values())

            # Cập nhật trọng số
            optimizer.zero_grad()
            losses.backward()
            optimizer.step()
            
            epoch_loss += losses.item()
            
            # Cập nhật giao diện thanh tiến trình
            pbar.set_postfix({"Loss": f"{losses.item():.4f}"})
            
            # Gửi log từng batch lên WandB
            logger.log_train_step(losses.item(), loss_dict['loss_classifier'].item(), loss_dict['loss_box_reg'].item())

        # Giảm learning rate theo lịch trình
        lr_scheduler.step()
        avg_train_loss = epoch_loss / len(train_loader)

        # --- BƯỚC 2: VALIDATION ---
        model.eval()
        print(f"⏳ Đang đánh giá mAP tập Validation...")
        
        val_pbar = tqdm(val_loader, desc=f"Epoch {epoch+1}/{args.epochs} [Val]")
        with torch.no_grad():
            for images, targets in val_pbar:
                images = list(img.to(device) for img in images)
                targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
                
                # Trích xuất dự đoán
                preds = model(images)
                evaluator.update(preds, targets)

        # ==========================================
        # 5. TÍNH TOÁN METRICS & LƯU TRỮ
        # ==========================================
        map_50, map_75 = evaluator.compute_and_reset()
        current_lr = optimizer.param_groups[0]['lr']
        
        print(f"📊 Kết quả Epoch {epoch+1}: Train Loss = {avg_train_loss:.4f} | mAP@50 = {map_50:.4f} | LR = {current_lr}")
        
        # Gửi log cuối epoch lên WandB
        logger.log_val_metrics(epoch+1, map_50, map_75, current_lr)
        
        # Cơ chế tự động lưu mô hình tốt nhất
        if map_50 > best_map:
            best_map = map_50
            best_model_path = os.path.join(args.project_dir, f"{args.name}_e{epoch+1}_best.pth")
            torch.save(model.state_dict(), best_model_path)
            print(f"🌟 Đã lưu kỷ lục mới tại: {best_model_path}")
            
        # Lưu file dự phòng của epoch hiện tại (đề phòng mất điện/đứt mạng)
        last_model_path = os.path.join(args.project_dir, f"{args.name}_e{epoch+1}_last.pth")
        torch.save(model.state_dict(), last_model_path)

    # ==========================================
    # 6. KẾT THÚC
    # ==========================================
    logger.finish()
    print("✅ Hoàn tất huấn luyện!")

if __name__ == '__main__':
    main()
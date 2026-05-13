from ultralytics import YOLO
import argparse
from config import parse_args
def main():
    # 1. Lấy tham số từ dòng lệnh
    args = parse_args()

    # Quản lý việc bật/tắt wandb cho YOLO
    import wandb
    if args.disable_wandb:
        wandb.init(mode="disabled") # Tắt hẳn wandb nếu gõ cờ --disable_wandb

    print(f"🚀 Đang khởi tạo mô hình YOLOv8 với tạ: {args.weights}")
    model = YOLO(args.weights)

    print(f"Bắt đầu huấn luyện phiên bản: {args.name} | Ảnh: {args.imgsz}x{args.imgsz}")
    
    # 2. Truyền tham số vào hàm train của YOLO
    results = model.train(
        data=args.data_yaml,
        epochs=args.epochs,
        batch=args.batch_size,
        imgsz=args.imgsz,
        project=args.project_dir,
        name=args.name,
        patience=args.patience,
        lr0=args.lr0,
        device=args.device,
        optimizer='AdamW', # Hardcode AdamW vì rất tốt cho y tế
        
        # Một số augmentation an toàn cho X-quang
        degrees=10.0,
        flipud=0.0,  # Cấm lật dọc ảnh X-quang
        fliplr=0.5   # Cho phép lật ngang
    )

    print(f"✅ Quá trình huấn luyện YOLO hoàn tất! Kết quả lưu tại: {args.project_dir}/{args.name}")

if __name__ == '__main__':
    main()
import argparse
from ultralytics import YOLO

def parse_args():
    parser = argparse.ArgumentParser(description="Huấn luyện YOLOv8 cho Object Detection (Khoanh vùng tổn thương phổi)")

    # ==========================================
    # 1. CẤU HÌNH DỮ LIỆU & LƯU TRỮ
    # ==========================================
    parser.add_argument('--data_yaml', type=str, default='lung_dataset.yaml',
                        help='Đường dẫn đến file cấu hình dataset (.yaml)')
    
    parser.add_argument('--project_dir', type=str, default='YOLO_Results',
                        help='Thư mục gốc để lưu toàn bộ kết quả train YOLO')
    
    parser.add_argument('--name', type=str, default='Lung_Lesion_v1',
                        help='Tên thư mục con của phiên bản chạy này (VD: v1_yolo_small)')

    # ==========================================
    # 2. CẤU HÌNH MÔ HÌNH (MODEL)
    # ==========================================
    parser.add_argument('--weights', type=str, default='yolov8s.pt',
                        help='Trọng số khởi tạo: yolov8n.pt (Nano), yolov8s.pt (Small), yolov8m.pt (Medium)')

    # ==========================================
    # 3. SIÊU THAM SỐ (HYPERPARAMETERS)
    # ==========================================
    parser.add_argument('--epochs', type=int, default=50,
                        help='Số vòng lặp huấn luyện tối đa')
    
    parser.add_argument('--batch_size', type=int, default=8,
                        help='Kích thước batch (Nên để 8 hoặc 16 tùy VRAM)')
    
    parser.add_argument('--imgsz', type=int, default=512,
                        help='Kích thước ảnh đầu vào (Khuyên dùng 512 hoặc 640 cho X-quang)')
    
    parser.add_argument('--patience', type=int, default=10,
                        help='Early stopping: Dừng sớm nếu không cải thiện sau N epoch')
    
    parser.add_argument('--lr0', type=float, default=0.001,
                        help='Tốc độ học (Learning Rate) ban đầu')

    parser.add_argument('--device', type=str, default='0',
                        help='Thiết bị huấn luyện: "0" cho GPU Nvidia, hoặc "cpu"')

    # ==========================================
    # 4. CÁC CỜ ĐIỀU KHIỂN
    # ==========================================
    parser.add_argument('--disable_wandb', action='store_true',
                        help='Cờ này để TẮT wandb (Mặc định YOLO tự bật wandb nếu đã cài)')

    return parser.parse_args()


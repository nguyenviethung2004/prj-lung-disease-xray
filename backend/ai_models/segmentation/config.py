import argparse # Thư viện để phân tích tham số dòng lệnh

def parse_args():
    """Hàm định nghĩa và phân tích các tham số truyền vào từ dòng lệnh."""
    parser = argparse.ArgumentParser(description="Huấn luyện mô hình UNet cho Segmentation")
    
    # 1. Tham số cho Dữ liệu (Data)
    parser.add_argument("--batch_size", type=int, default=4, help="Kích thước batch size")
    
    # 2. Tham số cho Huấn luyện (Training)
    parser.add_argument("--epochs", type=int, default=100, help="Số lượng epoch cần huấn luyện")
    parser.add_argument("--lr", type=float, default=0.0005, help="Learning rate (Tốc độ học)")
    parser.add_argument("--device", type=str, default="cuda", choices=["cuda", "cpu"], help="Thiết bị sử dụng (cuda hoặc cpu)")
    
    # 3. Tham số cho Lưu trữ (Saving/Logging)
    parser.add_argument("--version", type=str, default="v1.0", help="Đánh dấu phiên bản huấn luyện (VD: v1.0, v2_augment, test_lr)")
    parser.add_argument("--results_dir", type=str, default="results", help="Thư mục lưu mô hình và logs")
    parser.add_argument("--data_dir", type=str, default="lung_dataset/ChestXray", help="Thư mục lưu mô hình và logs")

    parser.add_argument("--model_name", type=str, default="unet-6v.pt", help="Tên file mô hình sẽ lưu")
    parser.add_argument("--log_file", type=str, default="train-log.txt", help="Tên file log quá trình huấn luyện")
# 3. Tham số cho Lưu trữ (Saving/Logging)
    parser.add_argument("--is_wandb", action="store_false", default=True, 
                        help="Mặc định là CÓ sử dụng W&B. Gõ --is_wandb nếu bạn muốn TẮT.")
    
    parser.add_argument("--is_txt", action="store_false", default=True, 
                        help="Mặc định là CÓ lưu log txt. Gõ --is_txt nếu bạn muốn TẮT.")
    # 4. Tham số mở rộng (Metrics) - Dành cho các metrics bạn mới tìm hiểu
    parser.add_argument("--calc_extra_metrics", action="store_true", help="Có tính thêm Pixel Acc, Precision, Recall, Specificity không (Mặc định: Không)")

    return parser.parse_args()

# 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


args = parse_args()
print("Tham số đã được phân tích:")
print(args)
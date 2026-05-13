import torch.optim as optim

class RSNAOptimizer:
    """
    Class quản lý Bộ tối ưu hóa (Optimizer) và Bộ điều phối tốc độ học (Scheduler).
    """
    def __init__(self, model_parameters, lr=1e-4, weight_decay=1e-2):
        """
        Args:
            model_parameters: Trọng số của mô hình (ví dụ: model.parameters())
            lr (float): Tốc độ học khởi tạo (Learning Rate).
            weight_decay (float): Hệ số phạt L2 để chống Overfitting.
        """
        # 1. Khởi tạo thuật toán AdamW
        self.optimizer = optim.AdamW(
            model_parameters, 
            lr=lr, 
            weight_decay=weight_decay
        )

        # 2. Khởi tạo Scheduler (Giảm tốc tự động)
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',      # Theo dõi Loss (càng nhỏ càng tốt)
            factor=0.1,      # Hệ số giảm: lr_mới = lr_cũ * 0.1
            patience=5,      # Sức chịu đựng: Đợi 5 epoch không cải thiện mới giảm
            min_lr=1e-6      # Mức tốc độ học thấp nhất cho phép (đáy)
        )

    def get_optimizer(self):
        """Trả về đối tượng optimizer để dùng trong vòng lặp train"""
        return self.optimizer

    def get_scheduler(self):
        """Trả về đối tượng scheduler để cập nhật sau mỗi epoch"""
        return self.scheduler
        
    def step_scheduler(self, val_loss):
        """Hàm bọc (wrapper) để cập nhật scheduler một cách gọn gàng"""
        self.scheduler.step(val_loss)
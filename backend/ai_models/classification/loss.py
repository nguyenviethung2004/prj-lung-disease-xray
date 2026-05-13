import torch
import torch.nn as nn
import torch.nn.functional as F

class BalancedFocalLoss(nn.Module):
    def __init__(self, class_counts, gamma=2.0):
        """
        Args:
            class_counts (list): Danh sách chứa số lượng ảnh của từng class.
                                 Ví dụ: [8851, 11821, 6012]
            gamma (float): Trọng số phạt các ca dự đoán sai (mặc định = 2.0)
        """
        super().__init__()
        self.gamma = gamma
        
        # ==========================================
        # BƯỚC 1: TÍNH TOÁN TOÁN HỌC CHO ALPHA
        # ==========================================
        # Chuyển list thành tensor
        counts = torch.tensor(class_counts, dtype=torch.float32)
        
        # Tính tổng số ảnh và số lượng class
        total_samples = counts.sum()
        num_classes = len(counts)
        
        # Công thức: Alpha_i = Tổng / (Số_Class * Số_Ảnh_Class_i)
        # Cách tính này đảm bảo class ít ảnh sẽ nhận alpha > 1, class nhiều ảnh nhận alpha < 1
        alpha_weights = total_samples / (num_classes * counts)
        
        # ==========================================
        # BƯỚC 2: QUẢN LÝ BỘ NHỚ THÔNG MINH
        # ==========================================
        # Sử dụng register_buffer thay vì khai báo biến thông thường.
        # Lý do: Khi bạn gọi model.to('cuda'), PyTorch sẽ tự động mang tensor 'alpha' này 
        # lên GPU cùng với model, giúp tránh lỗi lệch thiết bị (Device mismatch error).
        self.register_buffer('alpha', alpha_weights)

    def forward(self, logits, targets):
        # ==========================================
        # BƯỚC 3: LAN TRUYỀN TIẾN (FORWARD PASS)
        # ==========================================
        
        # A. Tính Cross Entropy nguyên bản (reduction='none' để lấy loss của từng ảnh, không lấy trung bình vội)
        ce_loss = F.cross_entropy(logits, targets, reduction='none')
        
        # B. Lấy lại xác suất dự đoán đúng (p_t)
        # Trick toán học: Vì CE = -ln(p_t) => p_t = e^(-CE)
        pt = torch.exp(-ce_loss)
        
        # C. Áp dụng Gamma: Ép mô hình tập trung vào ca khó
        # Công thức: (1 - p_t)^gamma * CE
        # Phân tích: Nếu mô hình đoán đúng (pt gần 1) -> (1-pt) gần 0 -> Loss bị triệt tiêu.
        focal_loss = ((1 - pt) ** self.gamma) * ce_loss
        
        # D. Áp dụng Alpha: Cân bằng số lượng dữ liệu
        # targets là tensor chứa nhãn (VD: [0, 2, 1, ...]). 
        # Lệnh self.alpha[targets] sẽ ánh xạ và nhặt ra đúng trọng số alpha cho từng ảnh trong batch.
        alpha_t = self.alpha[targets]
        
        # Nhân loss hiện tại với trọng số alpha tương ứng
        focal_loss = focal_loss * alpha_t
        
        # Trả về giá trị loss trung bình của toàn bộ batch
        return focal_loss.mean()    
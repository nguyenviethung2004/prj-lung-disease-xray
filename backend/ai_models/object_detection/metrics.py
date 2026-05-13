# metrics.py
from torchmetrics.detection.mean_ap import MeanAveragePrecision

class MAPEvaluator:
    def __init__(self):
        # Khởi tạo bộ tính mAP cho Bounding Box
        self.metric = MeanAveragePrecision(iou_type="bbox")

    def update(self, preds, targets):
        """Nạp dự đoán và nhãn thực tế của từng batch vào bộ nhớ"""
        self.metric.update(preds, targets)

    def compute_and_reset(self):
        """Tính toán kết quả cuối epoch và reset để dùng cho epoch sau"""
        result = self.metric.compute()
        map_50 = result['map_50'].item()
        map_75 = result['map_75'].item()
        
        # Reset lại bộ đếm
        self.metric.reset()
        return map_50, map_75
import torch

def get_predictions(y_pred):
    """
    Convert logits -> predicted class
    """
    return torch.argmax(y_pred, dim=1)



def classification_metrics(y_true, y_pred, num_classes=3, eps=1e-7):
    """
    Trả về:
    accuracy, precision, recall, f1, specificity (macro)
    Đã được tối ưu bằng Vectorization thay vì vòng lặp for.
    """
    y_pred = get_predictions(y_pred) # Đảm bảo y_true và y_pred là 1D tensor

    # 1. Tính Accuracy chung
    accuracy = (y_pred == y_true).float().mean()

    # 2. Tạo tensor các class (shape: [num_classes, 1]) để broadcasting
    # Ví dụ với 3 classes: [[0], [1], [2]]
    classes = torch.arange(num_classes, device=y_true.device).unsqueeze(1)

    # 3. Reshape labels và preds (shape: [1, batch_size])
    y_true_ext = y_true.unsqueeze(0)
    y_pred_ext = y_pred.unsqueeze(0)

    # 4. Tính toán boolean masks cho tất cả các class cùng lúc (shape: [num_classes, batch_size])
    is_pred_cls = (y_pred_ext == classes)
    is_true_cls = (y_true_ext == classes)

    # 5. Tính TP, FP, FN, TN cho mỗi class (sum theo batch, dim=1)
    tp = (is_pred_cls & is_true_cls).sum(dim=1).float()
    fp = (is_pred_cls & ~is_true_cls).sum(dim=1).float()
    fn = (~is_pred_cls & is_true_cls).sum(dim=1).float()
    tn = (~is_pred_cls & ~is_true_cls).sum(dim=1).float()

    # 6. Tính toán các chỉ số per-class
    precision_cls = tp / (tp + fp + eps)
    recall_cls = tp / (tp + fn + eps)
    
    # Tính trực tiếp F1 từ TP, FP, FN để tránh lỗi toán học khi phân số bằng 0
    f1_cls = 2 * tp / (2 * tp + fp + fn + eps)
    
    specificity_cls = tn / (tn + fp + eps)

    # 7. Tính Macro-average và trả về
    return (
        accuracy,
        precision_cls.mean(),
        recall_cls.mean(),
        f1_cls.mean(),
        specificity_cls.mean()
    )
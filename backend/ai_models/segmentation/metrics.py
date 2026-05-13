

def jaccard(y_true, y_pred):
    """ Jaccard a.k.a IoU score for batch of images
    """
    
    num = y_true.size(0)
    eps = 1e-7
    
    y_true_flat = y_true.view(num, -1)
    y_pred_flat = y_pred.view(num, -1)
    intersection = (y_true_flat * y_pred_flat).sum(1)
    union = ((y_true_flat + y_pred_flat) > 0.0).float().sum(1)
    
    score = (intersection) / (union + eps)
    score = score.sum() / num
    return score
    

def dice(y_true, y_pred):
    """ Dice a.k.a f1 score for batch of images
    """
    num = y_true.size(0)
    eps = 1e-7
    
    y_true_flat = y_true.view(num, -1)
    y_pred_flat = y_pred.view(num, -1)
    intersection = (y_true_flat * y_pred_flat).sum(1)
    
    score =  (2 * intersection) / (y_true_flat.sum(1) + y_pred_flat.sum(1) + eps)
    score = score.sum() / num
    return score



def precision_recall(y_true, y_pred):
    """ Tính Precision và Recall cho batch ảnh """
    num = y_true.size(0)
    eps = 1e-7
    
    # Duỗi thẳng ma trận giống như hàm jaccard/dice
    y_true_flat = y_true.view(num, -1)
    y_pred_flat = y_pred.view(num, -1)
    
    # Tính True Positives (Phần giao nhau - AI đoán đúng là phổi)
    true_positives = (y_true_flat * y_pred_flat).sum(1)
    
    # Tính tổng số pixel AI dự đoán là phổi
    predicted_positives = y_pred_flat.sum(1)
    
    # Tính tổng số pixel thực tế là phổi (Ground truth)
    actual_positives = y_true_flat.sum(1)
    
    # Tính toán
    precision = true_positives / (predicted_positives + eps)
    recall = true_positives / (actual_positives + eps)
    
    # Lấy trung bình cho cả batch
    precision = precision.sum() / num
    recall = recall.sum() / num
    
    return precision, recall


def accuracy_specificity(y_true, y_pred):
    """ Tính Accuracy (Độ chính xác tổng thể) và Specificity (Độ đặc hiệu) """
    num = y_true.size(0)
    eps = 1e-7
    
    # Duỗi thẳng ma trận
    y_true_flat = y_true.view(num, -1)
    y_pred_flat = y_pred.view(num, -1)
    
    # Tổng số pixel trên một ảnh
    total_pixels = y_true_flat.size(1)
    
    # Tính True Positives (Đoán đúng là Phổi) và True Negatives (Đoán đúng là Nền)
    tp = (y_true_flat * y_pred_flat).sum(1)
    tn = ((1 - y_true_flat) * (1 - y_pred_flat)).sum(1)
    
    # Tính tổng số pixel thực tế là Nền (Actual Negatives)
    actual_negatives = (1 - y_true_flat).sum(1)
    
    # Tính toán chỉ số
    accuracy = (tp + tn) / total_pixels
    specificity = tn / (actual_negatives + eps)
    
    # Lấy trung bình cho cả batch
    accuracy = accuracy.sum() / num
    specificity = specificity.sum() / num
    
    return accuracy, specificity
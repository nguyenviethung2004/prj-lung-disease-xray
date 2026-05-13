# model.py
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

def get_faster_rcnn_model(num_classes):
    """
    Khởi tạo mô hình Faster R-CNN với backbone ResNet50-FPN.
    Lưu ý: num_classes = Số loại bệnh + 1 (Background)
    """
    # Load trọng số mặc định (COCO) để hội tụ nhanh hơn
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights="DEFAULT")
    
    # Lấy số lượng kênh đầu vào của lớp phân loại cuối
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    
    # Thay thế Head cũ bằng Head mới với số class của bài toán X-quang
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    
    return model
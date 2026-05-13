import torch
import torch.nn as nn
from torchvision import models
import torchxrayvision as xrv

class RSNAResNet50(nn.Module):
    """
    Class định nghĩa mô hình ResNet50 tùy chỉnh cho bài toán phân loại X-quang RSNA (3 lớp).
    Áp dụng kỹ thuật Transfer Learning.
    """
    def __init__(self, num_classes=3, pretrained=True, freeze_backbone=False):
        """
        Args:
            num_classes (int): Số lượng lớp đầu ra (0: Normal, 1: Not Normal, 2: Lung Opacity).
            pretrained (bool): Nếu True, sử dụng trọng số pre-train từ ImageNet.
            freeze_backbone (bool): Nếu True, "đóng băng" (không cập nhật) trọng số phần thân ResNet.
        """
        super().__init__()
        
        # 1. Tải mô hình ResNet50 gốc
        # weights=models.ResNet50_Weights.DEFAULT là cách gọi mới chuẩn của PyTorch thay cho pretrained=True
        if pretrained:
            print("Đang tải mô hình ResNet50 với trọng số pre-train từ ImageNet...")
            self.model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        else:
            print("Đang khởi tạo mô hình ResNet50 với trọng số ngẫu nhiên...")
            self.model = models.resnet50(weights=None)

        # 2. Xử lý phần Thân (Backbone)
        if freeze_backbone and pretrained:
            print("Đã đóng băng phần thân (Backbone) của ResNet50. Chỉ huấn luyện phần đầu (Head).")
            for param in self.model.parameters():
                param.requires_grad = False
        else:
            print("Phần thân (Backbone) của ResNet50 sẽ được huấn luyện (Fine-tuning).")

        # 3. Thay thế phần Đầu (Classification Head)
        # ResNet50 gốc kết thúc bằng lớp: (fc): Linear(in_features=2048, out_features=1000, bias=True)
        # Chúng ta cần lấy ra số lượng feature đầu vào của lớp cuối cùng (thường là 2048)
        num_features = self.model.fc.in_features
        
        # Thiết kế lại Classification Head mới cho 3 lớp
        # Một cấu trúc đơn giản nhưng hiệu quả là: Linear -> ReLU -> Dropout -> Linear
        # dropout=0.5 giúp chống Overfitting rất tốt cho dữ liệu y tế.
        self.model.fc = nn.Sequential(
            nn.Linear(num_features, 512), # Lớp ẩn 1: 2048 -> 512
            nn.ReLU(inplace=True),        # Hàm kích hoạt ReLU
            nn.Dropout(p=0.5),             # Bỏ ngẫu nhiên 50% nơ-ron để chống học vẹt
            nn.Linear(512, num_classes)    # Lớp đầu ra: 512 -> num_classes (3)
        )

    def forward(self, x):
        """
        Lan truyền tiến (Forward pass).
        Args:
            x (Tensor): Tensor hình ảnh đầu vào [batch_size, 3, 224, 224].
        Returns:
            Logits (Tensor): Tensor đầu ra chứa điểm số chưa qua Softmax [batch_size, 3].
        """
        # Chạy ảnh qua toàn bộ kiến trúc mô hình đã được chỉnh sửa
        return self.model(x)

class RSNAEfficientNetB4(nn.Module):
    """
    Class định nghĩa mô hình EfficientNet-B4 cho bài toán phân loại X-quang RSNA (3 lớp).
    Kích thước ảnh đầu vào BẮT BUỘC KHUYẾN NGHỊ: 380x380.
    """
    def __init__(self, num_classes=3, pretrained=True, freeze_backbone=False):
        super().__init__()
        
        # 1. Tải mô hình EfficientNet-B4 gốc từ torchvision
        if pretrained:
            print("Đang tải mô hình EfficientNet-B4 (Weights: IMAGENET1K_V1)...")
            self.model = models.efficientnet_b4(weights=models.EfficientNet_B4_Weights.DEFAULT)
        else:
            print("Đang khởi tạo EfficientNet-B4 với trọng số ngẫu nhiên...")
            self.model = models.efficientnet_b4(weights=None)

        # 2. Xử lý phần Thân (Backbone)
        if freeze_backbone and pretrained:
            print("Đã đóng băng phần thân (Backbone). Chỉ huấn luyện phần đầu (Head).")
            for param in self.model.parameters():
                param.requires_grad = False
        else:
            print("Phần thân (Backbone) sẽ được huấn luyện (Fine-tuning).")

        # 3. Thay thế phần Đầu (Classification Head)
        # Khác với ResNet (dùng self.model.fc), phần đầu của EfficientNet nằm ở self.model.classifier
        # Cấu trúc gốc của nó là: Sequential( Dropout(p=0.4), Linear(in_features=1792, out_features=1000) )
        
        # Lấy số lượng feature đầu vào (với B4, con số này là 1792)
        num_features = self.model.classifier[1].in_features
        
        # Xây dựng lại Head mới cho 3 class
        self.model.classifier = nn.Sequential(
            nn.Dropout(p=0.5, inplace=True),  # Dropout mạnh ở đầu để chống Overfitting
            nn.Linear(num_features, 512),     # Lớp ẩn: 1792 -> 512
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.3),                # Thêm một lớp Dropout nhẹ nữa
            nn.Linear(512, num_classes)       # Lớp đầu ra: 512 -> 3
        )
        print(f"Đã thiết lập Classification Head mới cho {num_classes} lớp.")

    def forward(self, x):
        return self.model(x)
    


class RSNADenseNet121(nn.Module):
    def __init__(self, num_classes=3, pretrained=True):
        super().__init__()
        
        # 1. Tải lõi mô hình DenseNet121
        # Sử dụng cú pháp 'weights' hiện đại (thay vì 'pretrained=True' báo lỗi vàng)
        if pretrained:
            self.model = models.densenet121(weights=models.DenseNet121_Weights.DEFAULT)
        else:
            self.model = models.densenet121(weights=None)
            
        # 2. Bóc tách phần "Đầu" (Classification Head)
        # Trong ResNet, lớp cuối tên là 'fc'. Nhưng trong DenseNet, nó tên là 'classifier'
        # in_features của DenseNet121 mặc định là 1024
        num_features = self.model.classifier.in_features
        
        # 3. Lắp ráp cái "Đầu" mới cho bài toán RSNA (3 class)
        # Thêm vùng đệm (512) và Dropout để chống Overfitting trên tập y tế
        self.model.classifier = nn.Sequential(
            nn.Linear(num_features, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.5), # Tắt ngẫu nhiên 50% nơ-ron khi train
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        # Trả về giá trị thô (Raw Logits), tuyệt đối không dùng Sigmoid hay Softmax ở đây
        # Để nhường lại phần tính xác suất cho hàm Loss (BalancedFocalLoss)
        return self.model(x)



class RSNADenseNet_XRV(nn.Module):
    def __init__(self, num_classes=3):
        super(RSNADenseNet_XRV, self).__init__()

        self.model = xrv.models.DenseNet(weights="densenet121-res224-all")

        num_features = self.model.classifier.in_features

        self.model.classifier = nn.Sequential(
            nn.Linear(num_features, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.5), 
            nn.Linear(512, num_classes)
        )
        # 1. Tải lõi mô hình DenseNet121

    def forward(self, x):
        
        return self.model(x)


import torch
import torch.nn as nn
import timm

class RSNASwinSmall(nn.Module):
    def __init__(self, model_name='swin_small_patch4_window7_224', num_classes=3, pretrained=True):
        super(RSNASwinSmall, self).__init__()
        
        # 1. Khởi tạo mô hình Swin Small từ thư viện timm
        # Ta dùng bản patch4, window7, kích thước ảnh đầu vào mặc định 224x224
        self.model = timm.create_model(model_name, pretrained=pretrained)
        
        # 2. Chỉnh sửa lớp đầu tiên để nhận ảnh 1 kênh (Grayscale)
        # Mặc định Swin nhận 3 kênh (RGB). Ta thay đổi patch_embed.proj
        default_config = self.model.default_cfg
        original_proj = self.model.patch_embed.proj
        
        self.model.patch_embed.proj = nn.Conv2d(
            in_channels=1, # Chuyển từ 3 thành 1
            out_channels=original_proj.out_channels,
            kernel_size=original_proj.kernel_size,
            stride=original_proj.stride,
            padding=original_proj.padding
        )
        
        # Trọng số của kênh mới có thể được khởi tạo bằng trung bình cộng của 3 kênh cũ 
        # để tận dụng Pretrained weights tốt hơn
        if pretrained:
            with torch.no_state_dict():
                self.model.patch_embed.proj.weight[:] = original_proj.weight.sum(dim=1, keepdim=True)

        # 3. Chỉnh sửa lớp Head (Phân loại)
        # Swin dùng self.model.head làm lớp phân loại cuối cùng
        n_features = self.model.head.in_features
        self.model.head = nn.Linear(n_features, num_classes)

    def forward(self, x):
        # Đầu vào x: [Batch_size, 1, 224, 224]
        x = self.model(x)
        return x



# ==========================================
# TEST NHANH MÔ HÌNH (Chạy file này độc lập để kiểm tra)
# ==========================================
if __name__ == "__main__":
    # Khởi tạo thử mô hình
    model = RSNADenseNet121(num_classes=3)
    
    # Tạo một tensor ảnh rỗng (Batch Size=4, 3 Kênh màu, Kích thước 224x224)
    # Lưu ý: DenseNet có thể nhận ảnh to hơn (vd: 256x256, 380x380) tùy ý
    dummy_input = torch.randn(4, 3, 224, 224) 
    
    # Cho ảnh chạy qua mô hình
    outputs = model(dummy_input)
    
    print("Kiến trúc phần đầu (Classifier):")
    print(model.model.classifier)
    print(f"\nKích thước Tensor đầu ra (Dự kiến là [4, 3]): {outputs.shape}")
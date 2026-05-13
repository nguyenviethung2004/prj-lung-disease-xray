import torch
import torchvision


class Block(torch.nn.Module):
    def __init__(self, in_channels, mid_channel, out_channels, batch_norm=False):
        super().__init__()
        
        self.conv1 = torch.nn.Conv2d(in_channels=in_channels, out_channels=mid_channel, kernel_size=3, padding=1)
        self.conv2 = torch.nn.Conv2d(in_channels=mid_channel, out_channels=out_channels, kernel_size=3, padding=1)
        
        self.batch_norm = batch_norm
        if batch_norm:
            self.bn1 = torch.nn.BatchNorm2d(mid_channel)
            self.bn2 = torch.nn.BatchNorm2d(out_channels)
            
    def forward(self, x):
        x = self.conv1(x)
        if self.batch_norm:
            x = self.bn1(x)
        x = torch.nn.functional.relu(x, inplace=True)
        
        x = self.conv2(x)
        if self.batch_norm:
            x = self.bn2(x)
        out = torch.nn.functional.relu(x, inplace=True)
        return out
    

class UNet(torch.nn.Module):
    def up(self, x, size):
        return torch.nn.functional.interpolate(x, size=size, mode=self.upscale_mode)
    
    def down(self, x):
        return torch.nn.functional.max_pool2d(x, kernel_size=2)
    
    def __init__(self, in_channels, out_channels, batch_norm=False, upscale_mode="nearest"):
        super().__init__()
        
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.batch_norm = batch_norm
        self.upscale_mode = upscale_mode
        
        self.enc1 = Block(in_channels, 64, 64, batch_norm)
        self.enc2 = Block(64, 128, 128, batch_norm)
        self.enc3 = Block(128, 256, 256, batch_norm)
        self.enc4 = Block(256, 512, 512, batch_norm)
        
        self.center = Block(512, 1024, 512, batch_norm)
        
        self.dec4 = Block(1024, 512, 256, batch_norm)
        self.dec3 = Block(512, 256, 128, batch_norm)
        self.dec2 = Block(256, 128, 64, batch_norm)
        self.dec1 = Block(128, 64, 64, batch_norm)
        
        self.out = torch.nn.Conv2d(in_channels=64, out_channels=out_channels, kernel_size=1)

    def forward(self, x):
        enc1 = self.enc1(x)
        enc2 = self.enc2(self.down(enc1))
        enc3 = self.enc3(self.down(enc2))
        enc4 = self.enc4(self.down(enc3))
        
        center = self.center(self.down(enc4))
        
        dec4 = self.dec4(torch.cat([self.up(center, enc4.size()[-2:]), enc4], 1))
        dec3 = self.dec3(torch.cat([self.up(dec4, enc3.size()[-2:]), enc3], 1))
        dec2 = self.dec2(torch.cat([self.up(dec3, enc2.size()[-2:]), enc2], 1))
        dec1 = self.dec1(torch.cat([self.up(dec2, enc1.size()[-2:]), enc1], 1))
        
        out = self.out(dec1)
        
        return out
    

class PretrainedUNet(torch.nn.Module):
    def up(self, x, size):
        return torch.nn.functional.interpolate(x, size=size, mode=self.upscale_mode)

    def down(self, x):
        return torch.nn.functional.max_pool2d(x, kernel_size=2)

    def __init__(self, in_channels, out_channels, batch_norm=False, upscale_mode="nearest"):
        super().__init__()

        self.in_channels = in_channels
        self.out_channels = out_channels
        self.batch_norm = batch_norm
        self.upscale_mode = upscale_mode

        self.init_conv = torch.nn.Conv2d(in_channels, 3, 1)

        endcoder = torchvision.models.vgg11(pretrained=True).features
        self.conv1 = endcoder[0]   # 64
        self.conv2 = endcoder[3]   # 128
        self.conv3 = endcoder[6]   # 256
        self.conv3s = endcoder[8]  # 256
        self.conv4 = endcoder[11]   # 512
        self.conv4s = endcoder[13]  # 512
        self.conv5 = endcoder[16]  # 512
        self.conv5s = endcoder[18] # 512

        self.center = Block(512, 512, 256, batch_norm)

        self.dec5 = Block(512 + 256, 512, 256, batch_norm)
        self.dec4 = Block(512 + 256, 512, 128, batch_norm)
        self.dec3 = Block(256 + 128, 256, 64, batch_norm)
        self.dec2 = Block(128 + 64, 128, 32, batch_norm)
        self.dec1 = Block(64 + 32, 64, 32, batch_norm)

        self.out = torch.nn.Conv2d(in_channels=32, out_channels=out_channels, kernel_size=1)

    def forward(self, x):
        init_conv = torch.nn.functional.relu(self.init_conv(x), inplace=True)

        enc1 = torch.nn.functional.relu(self.conv1(init_conv), inplace=True)
        enc2 = torch.nn.functional.relu(self.conv2(self.down(enc1)), inplace=True)
        enc3 = torch.nn.functional.relu(self.conv3(self.down(enc2)), inplace=True)
        enc3 = torch.nn.functional.relu(self.conv3s(enc3), inplace=True)
        enc4 = torch.nn.functional.relu(self.conv4(self.down(enc3)), inplace=True)
        enc4 = torch.nn.functional.relu(self.conv4s(enc4), inplace=True)
        enc5 = torch.nn.functional.relu(self.conv5(self.down(enc4)), inplace=True)
        enc5 = torch.nn.functional.relu(self.conv5s(enc5), inplace=True)

        center = self.center(self.down(enc5))

        dec5 = self.dec5(torch.cat([self.up(center, enc5.size()[-2:]), enc5], 1))
        dec4 = self.dec4(torch.cat([self.up(dec5, enc4.size()[-2:]), enc4], 1))
        dec3 = self.dec3(torch.cat([self.up(dec4, enc3.size()[-2:]), enc3], 1))
        dec2 = self.dec2(torch.cat([self.up(dec3, enc2.size()[-2:]), enc2], 1))
        dec1 = self.dec1(torch.cat([self.up(dec2, enc1.size()[-2:]), enc1], 1))

        out = self.out(dec1)

        return out    
    




import torch
import torch.nn as nn
import torchvision.models as models

# --- 1. Lớp Block cho Decoder ---
class Block(nn.Module):
    def __init__(self, in_ch, mid_ch, out_ch, batch_norm=True):
        super().__init__()
        layers = [
            nn.Conv2d(in_ch, mid_ch, kernel_size=3, padding=1),
            nn.ReLU(inplace=True)
        ]
        if batch_norm:
            layers.insert(1, nn.BatchNorm2d(mid_ch))
        layers.extend([
            nn.Conv2d(mid_ch, out_ch, kernel_size=3, padding=1),
            nn.ReLU(inplace=True)
        ])
        if batch_norm:
            layers.insert(4, nn.BatchNorm2d(out_ch))
        self.double_conv = nn.Sequential(*layers)

    def forward(self, x):
        return self.double_conv(x)


# --- 2. Mô hình MobileNetV2-UNet ---
class MobileNetV2UNet(nn.Module):
    # Đã đổi mặc định out_channels=2 để phù hợp với Loss CrossEntropy
    def __init__(self, out_channels=2, batch_norm=True):
        super().__init__()
        
        # Load MobileNetV2 Pretrained
        base_model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
        encoder = base_model.features

        # ---------------------------------------------------------
        # SỬA TRỰC TIẾP LỚP ĐẦU TIÊN CỦA MOBILENETV2 (CÁCH 1)
        # Nhận vào 1 kênh (ảnh xám), thay vì 3 kênh mặc định.
        # ---------------------------------------------------------
        encoder[0][0] = nn.Conv2d(1, 32, kernel_size=3, stride=2, padding=1, bias=False)
        
        # --- ENCODER ---
        self.enc1 = encoder[0:2]   # 1/2 scale (256x256), 16 ch
        self.enc2 = encoder[2:4]   # 1/4 scale (128x128), 24 ch
        self.enc3 = encoder[4:7]   # 1/8 scale (64x64), 32 ch
        self.enc4 = encoder[7:14]  # 1/16 scale (32x32), 96 ch
        self.enc5 = encoder[14:19] # 1/32 scale (16x16), 1280 ch (Bottleneck)

        # --- BRIDGE ---
        self.center = Block(1280, 512, 512, batch_norm)

        # --- DECODER ---
        self.up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        
        self.dec5 = Block(512 + 96, 256, 256, batch_norm)
        self.dec4 = Block(256 + 32, 128, 128, batch_norm)
        self.dec3 = Block(128 + 24, 64, 64, batch_norm)
        self.dec2 = Block(64 + 16, 32, 32, batch_norm)
        
        # --- FINAL OUTPUT ---
        self.final_up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.final_out = nn.Conv2d(32, out_channels, kernel_size=1)

    def forward(self, x):
        # Đầu vào x: (Batch_size, 1, 512, 512)

        # Encoder
        e1 = self.enc1(x)     # 256x256, 16 ch
        e2 = self.enc2(e1)    # 128x128, 24 ch
        e3 = self.enc3(e2)    # 64x64, 32 ch
        e4 = self.enc4(e3)    # 32x32, 96 ch
        e5 = self.enc5(e4)    # 16x16, 1280 ch

        # Bridge
        c = self.center(e5)   # 16x16, 512 ch

        # Decoder + Skip connections
        d5 = self.dec5(torch.cat([self.up(c), e4], 1))   # 32x32
        d4 = self.dec4(torch.cat([self.up(d5), e3], 1))  # 64x64
        d3 = self.dec3(torch.cat([self.up(d4), e2], 1))  # 128x128
        d2 = self.dec2(torch.cat([self.up(d3), e1], 1))  # 256x256
        
        # Phóng to về 512x512 và xuất kết quả
        out = self.final_up(d2)     
        out = self.final_out(out)   
        
        # Đầu ra out: (Batch_size, 2, 512, 512)
        return out


import torch
import torch.nn as nn
import torchvision.models as models

# --- 1. Lớp Block cơ bản cho Decoder ---
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models

# --- Block Decoder ---
class Block(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),

            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.conv(x)

# --- Model ---
class ResNet18UNet(nn.Module):
    def __init__(self, out_channels=2):
        super().__init__()

        base = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)

        # ===== ENCODER =====
        self.init = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = base.bn1
        self.relu = base.relu
        self.maxpool = base.maxpool

        self.enc1 = base.layer1   # 64 ch
        self.enc2 = base.layer2   # 128 ch
        self.enc3 = base.layer3   # 256 ch
        self.enc4 = base.layer4   # 512 ch

        # ===== DECODER =====
        self.dec4 = Block(512 + 256, 256)
        self.dec3 = Block(256 + 128, 128)
        self.dec2 = Block(128 + 64, 64)
        self.dec1 = Block(64 + 64, 32)

        self.final = nn.Conv2d(32, out_channels, kernel_size=1)

    def forward(self, x):
        # ===== Encoder =====
        x1 = self.relu(self.bn1(self.init(x)))   # 1/2
        x2 = self.maxpool(x1)                    # 1/4

        e1 = self.enc1(x2)   # 1/4
        e2 = self.enc2(e1)   # 1/8
        e3 = self.enc3(e2)   # 1/16
        e4 = self.enc4(e3)   # 1/32

        # ===== Decoder =====
        d4 = self.dec4(torch.cat([
            F.interpolate(e4, size=e3.shape[2:], mode='bilinear', align_corners=True),
            e3
        ], dim=1))

        d3 = self.dec3(torch.cat([
            F.interpolate(d4, size=e2.shape[2:], mode='bilinear', align_corners=True),
            e2
        ], dim=1))

        d2 = self.dec2(torch.cat([
            F.interpolate(d3, size=e1.shape[2:], mode='bilinear', align_corners=True),
            e1
        ], dim=1))

        d1 = self.dec1(torch.cat([
            F.interpolate(d2, size=x1.shape[2:], mode='bilinear', align_corners=True),
            x1
        ], dim=1))

        out = self.final(F.interpolate(d1, size=x.shape[2:], mode='bilinear', align_corners=True))

        return out
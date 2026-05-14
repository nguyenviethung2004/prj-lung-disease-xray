import os
import cv2
import torch
import numpy as np
from PIL import Image
from torchvision import transforms

from ai_models.segmentation.unet_models import ResNet18UNet


# =========================
# 1. LOAD MODEL
# =========================
def load_unet_model(device, model_path: str):
    model = ResNet18UNet(out_channels=2)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()
    return model


# =========================
# 2. GET MASK
# =========================
def get_unet_mask(image_rgb, model, device):
    transform = transforms.Compose([
        transforms.Resize((512, 512)),
        transforms.Grayscale(num_output_channels=1),
        transforms.ToTensor(),
    ])

    input_tensor = transform(image_rgb).unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(input_tensor)

    # Case 1: 1 channel (sigmoid)
    if output.shape[1] == 1:
        prob = torch.sigmoid(output)
        mask = prob[0, 0].cpu().numpy()
        mask = (mask > 0.5).astype(np.uint8) * 255

    # Case 2: multi-class (softmax / CE)
    else:
        mask = torch.argmax(output, dim=1)[0].cpu().numpy()
        mask = (mask > 0).astype(np.uint8) * 255

    return mask


# =========================
# 3. CROP LUNG
# =========================
def crop_lung(image_bgr, mask_256,
              min_area_ratio=0.15,
              padding_percent=0.05):

    H, W = image_bgr.shape[:2]

    mask = cv2.resize(mask_256, (W, H), interpolation=cv2.INTER_NEAREST)

    # fallback nếu mask quá nhỏ
    if np.sum(mask == 255) / (H * W) < min_area_ratio:
        pad_h, pad_w = int(H * 0.1), int(W * 0.1)
        return image_bgr, image_bgr[pad_h:H-pad_h, pad_w:W-pad_w], pad_w, pad_h

    # convex hull
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    hull_mask = np.zeros_like(mask)

    for cnt in contours:
        if cv2.contourArea(cnt) > 500:
            hull = cv2.convexHull(cnt)
            cv2.drawContours(hull_mask, [hull], -1, 255, -1)

    final_cnts, _ = cv2.findContours(hull_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not final_cnts:
        return image_bgr, image_bgr, 0, 0

    all_pts = np.vstack(final_cnts)
    x, y, w, h = cv2.boundingRect(all_pts)

    pad_x = int(W * padding_percent)
    pad_y = int(H * padding_percent)

    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(W, x + w + pad_x)
    y2 = min(H, y + h + pad_y)

    cropped = image_bgr[y1:y2, x1:x2]

    return image_bgr, cropped, x1, y1


# =========================
# 4. MAIN PREDICT FUNCTION
# =========================
def predict_crop(model, input_data, device=None):
    """
    INPUT:
        - model: loaded UNet model
        - input_data: image path (str) OR image array (numpy BGR)
        - device: torch device (optional if model already on device)
    OUTPUT:
        - original image (numpy BGR)
        - cropped lung image (numpy BGR)
        - x1 offset
        - y1 offset
    """
    if device is None:
        device = next(model.parameters()).device

    # Handle input type
    if isinstance(input_data, str):
        image_bgr = cv2.imread(input_data)
        if image_bgr is None:
            raise ValueError(f"Cannot read image from path: {input_data}")
    else:
        # Assume it's a numpy array
        image_bgr = input_data

    image_rgb = Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))

    # predict mask
    mask = get_unet_mask(image_rgb, model, device)

    # crop
    original, cropped, x1, y1 = crop_lung(image_bgr, mask)

    return original, cropped, x1, y1

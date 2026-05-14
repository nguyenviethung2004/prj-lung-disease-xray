import torch
import cv2
import numpy as np
from PIL import Image
from torchvision import transforms

from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from pytorch_grad_cam.utils.image import show_cam_on_image

from ai_models.classification.classification_models import RSNADenseNet121
from core.config import settings

IMAGE_SIZE = settings.IMAGE_SIZE_CLASSIFICATION
CLASSES = ['Normal', 'COVID-19', 'Pneumonia']


def load_model_classification(device, model_path=str):
    model = RSNADenseNet121()
    checkpoint = torch.load(model_path, map_location=device)

    if 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    elif 'state_dict' in checkpoint:
        model.load_state_dict(checkpoint['state_dict'])
    else:
        model.load_state_dict(checkpoint)

    model.to(device)
    model.eval()
    return model


def preprocess_image(input_data):
    if isinstance(input_data, str):
        img_bgr = cv2.imread(input_data, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise ValueError(f"Không đọc được ảnh từ path: {input_data}")
    else:
        # Assume it's a numpy array
        img_bgr = input_data

    h, w = img_bgr.shape[:2]
    rgb_img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    
    # Maintain aspect ratio with padding (letterboxing)
    ratio = IMAGE_SIZE / max(h, w)
    new_h, new_w = int(h * ratio), int(w * ratio)
    resized = cv2.resize(rgb_img, (new_w, new_h))
    
    # Create black canvas and paste resized image in center
    canvas = np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)
    pad_y = (IMAGE_SIZE - new_h) // 2
    pad_x = (IMAGE_SIZE - new_w) // 2
    canvas[pad_y:pad_y+new_h, pad_x:pad_x+new_w] = resized
    
    rgb_img_float = np.float32(canvas) / 255.0

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    pil_img = Image.fromarray(canvas)
    tensor = transform(pil_img).unsqueeze(0)

    # Return padding info to map back
    return tensor, rgb_img_float, (pad_x, pad_y, new_w, new_h)


def get_target_layer(model):
    try:
        return [model.model.features[-1]]
    except:
        return [model.densenet.features[-1]]


def inference_with_gradcam(model, input_data, device):
    input_tensor, rgb_img_padded, (px, py, nw, nh) = preprocess_image(input_data)
    input_tensor = input_tensor.to(device)

    with torch.no_grad():
        output = model(input_tensor)
        prob = torch.nn.functional.softmax(output[0], dim=0)
        conf, cls = torch.max(prob, 0)

    class_idx = cls.item()
    confidence = float(conf.item() * 100)
    label = CLASSES[class_idx]

    cam = GradCAM(model=model, target_layers=get_target_layer(model))
    targets = [ClassifierOutputTarget(class_idx)]

    # Generate the activation mask for the padded image
    grayscale_cam = cam(input_tensor=input_tensor, targets=targets)[0]
    
    # Crop the padding back to get ONLY the lung area
    grayscale_lung = grayscale_cam[py:py+nh, px:px+nw]
    
    # Resize grayscale mask back to original input size
    orig_h, orig_w = (input_data.shape[:2]) if not isinstance(input_data, str) else (cv2.imread(input_data).shape[:2])
    grayscale_final = cv2.resize(grayscale_lung, (orig_w, orig_h))

    # Generate colorized gradcam image (standard way)
    gradcam_image_full = show_cam_on_image(rgb_img_padded, grayscale_cam, use_rgb=True)
    gradcam_image_cropped = gradcam_image_full[py:py+nh, px:px+nw]
    gradcam_image_final = cv2.resize(gradcam_image_cropped, (orig_w, orig_h))

    return grayscale_final, gradcam_image_final, label, confidence

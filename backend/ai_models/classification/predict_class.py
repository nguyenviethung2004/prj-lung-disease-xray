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

    rgb_img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    rgb_img = cv2.resize(rgb_img, (IMAGE_SIZE, IMAGE_SIZE))
    rgb_img_float = np.float32(rgb_img) / 255.0

    transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    pil_img = Image.fromarray(rgb_img)
    tensor = transform(pil_img).unsqueeze(0)

    return tensor, rgb_img_float


def get_target_layer(model):
    try:
        return [model.model.features[-1]]
    except:
        return [model.densenet.features[-1]]


def inference_with_gradcam(model, input_data, device):
    input_tensor, rgb_img = preprocess_image(input_data)
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

    grayscale_cam = cam(input_tensor=input_tensor, targets=targets)[0]

    gradcam_image = show_cam_on_image(rgb_img, grayscale_cam, use_rgb=True)
    return rgb_img, gradcam_image, label, confidence

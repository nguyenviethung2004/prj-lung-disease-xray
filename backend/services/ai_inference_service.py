import os
import cv2
import time
import base64
import numpy as np
from fastapi import UploadFile
from core.ai_models import AIModelManager
from core.logger import logger
from ai_models.classification.predict_class import inference_with_gradcam
from ai_models.object_detection.predict_object import inference_faster_rcnn
from ai_models.segmentation.predict_unet import predict_crop
import time
from starlette.concurrency import run_in_threadpool
import uuid
import shutil
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import UploadedImage, Prediction, AIModel, Class

models_manager = AIModelManager()
# Ensure directories exist
UPLOAD_DIR = "static/uploads"
RESULT_DIR = "static/results"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

def encode_image_base64(image_bgr):
    """
    Cho đầu vào là ảnh BGR (định dạng mặc định của OpenCV).
    """
    _, buffer = cv2.imencode(".jpg", image_bgr)
    img_base64 = base64.b64encode(buffer).decode("utf-8")
    return img_base64

def process_ai_pipeline(image_bgr):
    start_time = time.time()

    # Lưu ảnh gốc
    image_original_bgr = image_bgr.copy()

    # ================= SEGMENTATION =================
    _, cropped_bgr, crop_x1, crop_y1 = predict_crop(
        models_manager.segmentation_model,
        image_bgr,
        models_manager.device
    )
    logger.info(f"Đã hoàn thành segmentation. Crop offsets: x={crop_x1}, y={crop_y1}")

    # ================= CLASSIFICATION =================
    _, gradcam_rgb, label, confidence = inference_with_gradcam(
        models_manager.classification_model,
        cropped_bgr,
        models_manager.device
    )
    logger.info("Đã hoàn thành classification")

    analysis_type = "classification"
    boxes = []
    # Khởi tạo result_image_bgr là ảnh gốc
    result_image_bgr = image_original_bgr.copy()

    # ================= DECISION =================
    if label == "Normal":
        logger.info("Kết quả là Normal, không cần chạy detection")

    elif label == "COVID-19":
        # Resize gradcam_rgb (đang ở size 224x224) về lại kích thước vùng crop
        crop_h, crop_w = cropped_bgr.shape[:2]
        gradcam_resized = cv2.resize(gradcam_rgb, (crop_w, crop_h))
        gradcam_bgr = cv2.cvtColor(gradcam_resized, cv2.COLOR_RGB2BGR)
        
        # Overlay heatmap lên vùng crop trên ảnh gốc
        result_image_bgr[crop_y1:crop_y1+crop_h, crop_x1:crop_x1+crop_w] = gradcam_bgr
        logger.info("Kết quả là COVID-19, đã overlay Grad-CAM lên ảnh gốc")

    else:
        detect_image_rgb, detection_results = inference_faster_rcnn(
            models_manager.detection_model,
            cropped_bgr,
            models_manager.device
        )
        # Map bboxes back to original image coordinates
        mapped_boxes = []
        for res in detection_results:
            bbox = res["bbox"] # [x1, y1, x2, y2] relative to crop
            mapped_bbox = [
                bbox[0] + crop_x1,
                bbox[1] + crop_y1,
                bbox[2] + crop_x1,
                bbox[3] + crop_y1
            ]
            res["bbox"] = mapped_bbox
            mapped_boxes.append(res)
        
        # Với detection, ta không vẽ lên result_image_bgr vì frontend sẽ tự vẽ bbox
        # Nhưng ta vẫn trả về ảnh gốc (đã copy vào result_image_bgr ở trên)
        logger.info("Kết quả là bệnh phổi, đã chạy detection và map tọa độ về ảnh gốc")
        analysis_type = "detection"
        boxes = mapped_boxes

    processing_time = time.time() - start_time
    logger.info(f"Thời gian xử lý pipeline: {processing_time:.2f} giây")
    return {
        "label": label,
        "confidence": float(confidence),
        "analysis_type": analysis_type,
        "processing_time": round(processing_time, 2),
        "result_image_bgr": result_image_bgr,
        "original_image_bgr": image_original_bgr,
        "boxes": boxes if analysis_type == "detection" else []
    }




async def get_or_create_class(db: AsyncSession, class_name: str):
    query = select(Class).where(Class.ClassName == class_name)
    result = await db.execute(query)
    obj = result.scalar_one_or_none()
    if not obj:
        obj = Class(ClassName=class_name)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
    return obj

async def get_or_create_model(db: AsyncSession, model_name: str, version: str = "v1"):
    query = select(AIModel).where(AIModel.ModelName == model_name, AIModel.Version == version)
    result = await db.execute(query)
    obj = result.scalar_one_or_none()
    if not obj:
        obj = AIModel(ModelName=model_name, Version=version)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
    return obj

async def run_inference(file: UploadFile, db: AsyncSession, user_id: int):
    try:
        # 1. Save uploaded file to disk
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Reset file cursor before reading
        await file.seek(0)
        contents = await file.read()
        
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
            
        # 2. Save UploadedImage record to DB with path
        uploaded_image = UploadedImage(
            UserID=user_id,
            ImagePath=file_path.replace("\\", "/"),
            OriginalFileName=file.filename,
            Status="predicted"
        )
        db.add(uploaded_image)
        await db.commit()
        await db.refresh(uploaded_image)

        # 3. Read image for AI processing
        np_arr = np.frombuffer(contents, np.uint8)
        image_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if image_bgr is None:
            raise ValueError("Không đọc được ảnh")

        logger.info(f"Đã đọc ảnh thành công: {file.filename} (shape: {image_bgr.shape})")

        # 4. Gọi pipeline
        result = await run_in_threadpool(process_ai_pipeline, image_bgr)

        # 5. Save Result Image / Heatmap to disk
        result_filename = f"result_{unique_filename}"
        result_path = os.path.join(RESULT_DIR, result_filename)
        cv2.imwrite(result_path, result["result_image_bgr"])

        # 6. Get/Create Class and Model metadata
        class_obj = await get_or_create_class(db, result["label"])
        model_obj = await get_or_create_model(db, "LungDiseasePipeline")

        # 7. Save Prediction record to DB with path
        import json
        prediction = Prediction(
            ImageID=uploaded_image.ImageID,
            ModelID=model_obj.ModelID,
            PredictedClassID=class_obj.ClassID,
            Confidence=result["confidence"],
            HeatmapPath=result_path.replace("\\", "/"),
            InferenceTimeMs=result["processing_time"] * 1000,
            AIBoxes=json.dumps(result["boxes"]) if result.get("boxes") else None
        )
        db.add(prediction)
        await db.commit()
        await db.refresh(prediction)

        logger.info(f"Hoàn thành xử lý file: {file.filename}")

        return {
            "success": True,
            "message": "Inference completed and saved to disk",
            "prediction_id": prediction.PredictionID,
            "image_id": uploaded_image.ImageID,
            "label": result["label"],
            "confidence": result["confidence"],
            "analysis_type": result["analysis_type"],
            "processing_time": result["processing_time"],
            "result_image": encode_image_base64(result["result_image_bgr"]),
            "original_image": encode_image_base64(result["original_image_bgr"]),
            "boxes": result.get("boxes", [])
        }

    except Exception as e:
        logger.error(f"Lỗi xử lý AI Inference: {e}")
        await db.rollback()
        return {
            "success": False,
            "message": str(e),
        }

async def get_doctor_pending_images_service(db: AsyncSession, user_id: int):
    """
    Get images uploaded by this doctor that haven't been reviewed yet.
    """
    from models import DoctorReview
    
    query = (
        select(UploadedImage, Prediction, Class.ClassName)
        .join(Prediction, UploadedImage.ImageID == Prediction.ImageID)
        .join(Class, Prediction.PredictedClassID == Class.ClassID)
        .outerjoin(DoctorReview, Prediction.PredictionID == DoctorReview.PredictionID)
        .where(UploadedImage.UserID == user_id)
        .where(DoctorReview.ReviewID == None)
        .order_by(UploadedImage.UploadedAt.desc())
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    pending = []
    for img, pred, class_name in rows:
        pending.append({
            "image_id": img.ImageID,
            "prediction_id": pred.PredictionID,
            "filename": img.OriginalFileName,
            "image_path": img.ImagePath,
            "heatmap_path": pred.HeatmapPath,
            "created_at": img.UploadedAt,
            "ai_label": class_name,
            "confidence": pred.Confidence,
            "ai_boxes": pred.AIBoxes
        })
    return pending
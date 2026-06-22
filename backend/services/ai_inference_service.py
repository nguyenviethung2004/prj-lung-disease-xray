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
    grayscale_cam, gradcam_rgb, label, confidence = inference_with_gradcam(
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
        # 1. Colorize the heatmap
        heatmap_bgr = cv2.applyColorMap(np.uint8(255 * grayscale_cam), cv2.COLORMAP_JET)
        
        # 2. Use grayscale_cam as the alpha mask (normalized 0.0 to 1.0)
        # Smooth the mask to make the transition even more natural
        mask = cv2.GaussianBlur(grayscale_cam, (15, 15), 0)
        mask = np.expand_dims(mask, axis=-1) # Shape (H, W, 1)
        
        # 3. Perform pixel-wise alpha blending on the ROI
        h_h, h_w = heatmap_bgr.shape[:2]
        roi = image_original_bgr[crop_y1:crop_y1+h_h, crop_x1:crop_x1+h_w].astype(float)
        heatmap_f = heatmap_bgr.astype(float)
        
        # Blend: original * (1 - mask*alpha) + heatmap * (mask*alpha)
        # We cap the max intensity of heatmap at 0.5 for better visibility of lungs
        alpha_intensity = 0.5 
        blended_roi = roi * (1.0 - mask * alpha_intensity) + heatmap_f * (mask * alpha_intensity)
        blended_roi = np.clip(blended_roi, 0, 255).astype(np.uint8)
        
        # 4. Paste back
        result_image_bgr[crop_y1:crop_y1+h_h, crop_x1:crop_x1+h_w] = blended_roi
        
        logger.info("Kết quả là COVID-19, đã hòa trộn pixel-wise mượt mà không còn vệt xanh")

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

async def run_inference(file: UploadFile = None, db: AsyncSession = None, user_id: int = None, patient_code: str = None, image_id: int = None):
    try:
        if image_id is not None:
            # 1. Fetch existing UploadedImage
            stmt = select(UploadedImage).where(UploadedImage.ImageID == image_id)
            res = await db.execute(stmt)
            uploaded_image = res.scalar_one_or_none()
            if not uploaded_image:
                raise ValueError("Image ID not found in database")
            
            if patient_code:
                uploaded_image.PatientCode = patient_code
                db.add(uploaded_image)
                await db.commit()
                await db.refresh(uploaded_image)
            
            file_path = uploaded_image.ImagePath
            if not os.path.exists(file_path):
                raise ValueError(f"Image file not found on server disk: {file_path}")
                
            with open(file_path, "rb") as f:
                contents = f.read()
                
            unique_filename = os.path.basename(file_path)
            original_filename = uploaded_image.OriginalFileName
        else:
            if not file:
                raise ValueError("File is required when image_id is not provided")
            
            # Check if this patient already has an image with the same original filename
            stmt_exist = select(UploadedImage).where(
                UploadedImage.PatientCode == patient_code,
                UploadedImage.OriginalFileName == file.filename
            )
            res_exist = await db.execute(stmt_exist)
            existing_image = res_exist.scalars().first()
            
            if existing_image:
                logger.info(f"Ảnh '{file.filename}' cho bệnh nhân '{patient_code}' đã tồn tại (ImageID: {existing_image.ImageID}). Sử dụng lại bản ghi cũ.")
                uploaded_image = existing_image
                file_path = uploaded_image.ImagePath
                if not os.path.exists(file_path):
                    raise ValueError(f"Image file not found on server disk: {file_path}")
                with open(file_path, "rb") as f:
                    contents = f.read()
                unique_filename = os.path.basename(file_path)
                original_filename = uploaded_image.OriginalFileName
            else:
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
                    Status="predicted",
                    PatientCode=patient_code
                )
                db.add(uploaded_image)
                await db.commit()
                await db.refresh(uploaded_image)
                original_filename = file.filename

        # 3. Read image for AI processing
        np_arr = np.frombuffer(contents, np.uint8)
        image_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if image_bgr is None:
            raise ValueError("Không đọc được ảnh")

        logger.info(f"Đã đọc ảnh thành công: {original_filename} (shape: {image_bgr.shape})")

        # 4. Gọi pipeline
        result = await run_in_threadpool(process_ai_pipeline, image_bgr)

        # 5. Save Result Image / Heatmap to disk
        result_filename = f"result_{unique_filename}"
        result_path = os.path.join(RESULT_DIR, result_filename)
        cv2.imwrite(result_path, result["result_image_bgr"])

        # Check if a prediction already exists for this image
        stmt_pred = select(Prediction).where(Prediction.ImageID == uploaded_image.ImageID).order_by(Prediction.PredictionID.asc())
        res_pred = await db.execute(stmt_pred)
        existing_prediction = res_pred.scalars().first()

        if existing_prediction is not None:
            logger.info(f"Ảnh đã được predict trước đó (PredictionID: {existing_prediction.PredictionID}). Chạy ở chế độ xem, không lưu DB.")
            return {
                "success": True,
                "message": "Inference completed (view only, not saved to DB)",
                "prediction_id": existing_prediction.PredictionID,
                "image_id": uploaded_image.ImageID,
                "label": result["label"],
                "confidence": result["confidence"],
                "analysis_type": result["analysis_type"],
                "processing_time": result["processing_time"],
                "result_image": encode_image_base64(result["result_image_bgr"]),
                "original_image": encode_image_base64(result["original_image_bgr"]),
                "boxes": result.get("boxes", [])
            }

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

        logger.info(f"Hoàn thành xử lý file: {original_filename}")

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
    from sqlalchemy import func
    
    # Subquery to get the latest prediction ID for each image
    subq = (
        select(
            Prediction.ImageID,
            func.max(Prediction.PredictionID).label("latest_pred_id")
        )
        .group_by(Prediction.ImageID)
        .subquery()
    )
    
    query = (
        select(UploadedImage, Prediction, Class.ClassName)
        .join(subq, UploadedImage.ImageID == subq.c.ImageID)
        .join(Prediction, Prediction.PredictionID == subq.c.latest_pred_id)
        .join(Class, Prediction.PredictedClassID == Class.ClassID)
        .where(UploadedImage.UserID == user_id)
        .where(UploadedImage.Status != "reviewed")
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
            "ai_boxes": pred.AIBoxes,
            "patient_code": img.PatientCode
        })
    return pending
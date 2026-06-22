from fastapi import APIRouter, UploadFile, HTTPException, Depends, Form
from schemas.inference_schema import InferenceResponse
from services.ai_inference_service import run_inference, get_doctor_pending_images_service
from core.logger import logger
from core.db_session import get_async_db
from sqlalchemy.ext.asyncio import AsyncSession
from utils.jwt_manager import get_current_user

router = APIRouter(prefix="", tags=["AI Inference"])

from models import Class
from sqlalchemy import select

@router.get("/classes")
async def get_all_classes(db: AsyncSession = Depends(get_async_db)):
    """
    Fetch all available disease classes from database.
    """
    try:
        query = select(Class)
        result = await db.execute(query)
        classes = result.scalars().all()
        return [{"id": c.ClassID, "name": c.ClassName} for c in classes]
    except Exception as e:
        logger.error(f"Error fetching classes: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch classes")

@router.get("/doctor/pending-images")
async def get_pending_images(
    db: AsyncSession = Depends(get_async_db),
    current_user_id: str = Depends(get_current_user)
):
    """
    Get all images uploaded by the current doctor that are waiting for review.
    """
    try:
        return await get_doctor_pending_images_service(db, int(current_user_id))
    except Exception as e:
        logger.error(f"Error fetching pending images: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict", response_model=InferenceResponse)
async def predict_xray(
    file: UploadFile = None, 
    image_id: int = Form(None),
    patient_code: str = Form(None),
    db: AsyncSession = Depends(get_async_db),
    current_user_id: str = Depends(get_current_user)
):
    """
    Endpoint for doctors to upload an X-ray image and get AI analysis results.
    Results are saved to database.
    """
    if file is None and image_id is None:
        raise HTTPException(status_code=400, detail="Either file or image_id must be provided")

    if file is not None:
        if not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
            raise HTTPException(status_code=400, detail="Only JPG, JPEG, PNG are supported")
    
    import re
    if not patient_code:
        raise HTTPException(status_code=400, detail="Mã bệnh nhân là bắt buộc")
        
    patient_code = patient_code.strip()
    if not re.match(r"^[a-zA-Z0-9]+$", patient_code):
        raise HTTPException(status_code=400, detail="Mã bệnh nhân chỉ được chứa chữ cái và số viết liền không dấu")
    
    try:
        result = await run_inference(
            file=file,
            db=db,
            user_id=int(current_user_id),
            patient_code=patient_code,
            image_id=image_id
        )
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("message"))
        return result
    except Exception as e:
        logger.error(f"Prediction API error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/check-image-exists")
async def check_image_exists(
    filename: str,
    db: AsyncSession = Depends(get_async_db),
    current_user_id: str = Depends(get_current_user)
):
    """
    Check if an image with the given filename was already uploaded by this user.
    If found, return the patient_code and image_id.
    """
    from models import UploadedImage
    try:
        query = (
            select(UploadedImage)
            .where(UploadedImage.OriginalFileName == filename)
            .where(UploadedImage.UserID == int(current_user_id))
            .order_by(UploadedImage.UploadedAt.desc())
            .limit(1)
        )
        result = await db.execute(query)
        img = result.scalar_one_or_none()
        if img:
            return {
                "exists": True,
                "patient_code": img.PatientCode,
                "image_id": img.ImageID
            }
        return {"exists": False}
    except Exception as e:
        logger.error(f"Error checking image existence: {e}")
        return {"exists": False}

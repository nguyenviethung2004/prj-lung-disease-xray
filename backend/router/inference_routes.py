from fastapi import APIRouter, UploadFile, HTTPException, Depends
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
    file: UploadFile, 
    db: AsyncSession = Depends(get_async_db),
    current_user_id: str = Depends(get_current_user)
):
    """
    Endpoint for doctors to upload an X-ray image and get AI analysis results.
    Results are saved to database.
    """
    if not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
        raise HTTPException(status_code=400, detail="Only JPG, JPEG, PNG are supported")
    
    try:
        result = await run_inference(file, db, int(current_user_id))
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("message"))
        return result
    except Exception as e:
        logger.error(f"Prediction API error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

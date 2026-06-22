from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.db_session import get_async_db
from schemas.lung_disease_schema import DoctorReviewCreate, DoctorReviewOut
from services.review_service import submit_review_service, get_dashboard_stats_service, get_all_reviews_service, search_patient_records_service
from utils.jwt_manager import get_current_user, RoleChecker

router = APIRouter(prefix="/reviews", tags=["Doctor Reviews"])

@router.post("/", response_model=DoctorReviewOut)
async def submit_review(
    data: DoctorReviewCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user_id: str = Depends(get_current_user)
):
    """
    Endpoint for doctors to review and correct AI predictions.
    """
    # Ensure current user is the one submitting
    if int(current_user_id) != data.DoctorID:
        raise HTTPException(status_code=403, detail="Unauthorized to submit review for another doctor")
    
    return await submit_review_service(db, data)

@router.get("/dashboard-stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_async_db),
    _ = Depends(RoleChecker(["Superadmin"])) # Only Superadmin can see dashboard
):
    """
    Endpoint for admins to get system-wide statistics.
    """
    return await get_dashboard_stats_service(db)

@router.get("/list")
async def list_all_reviews(
    page: int = 1,
    page_size: int = 10,
    class_id: int = None,
    min_confidence: float = None,
    max_confidence: float = None,
    doctor_id: int = None,
    is_corrected: bool = None,
    start_date: str = None,
    end_date: str = None,
    db: AsyncSession = Depends(get_async_db),
    _ = Depends(RoleChecker(["admin", "Superadmin"]))
):
    """
    Endpoint for admins to list all doctor reviews with pagination and filtering.
    """
    return await get_all_reviews_service(
        db, page, page_size, 
        class_id, min_confidence, max_confidence, 
        doctor_id, is_corrected, start_date, end_date
    )

@router.get("/search-patient")
async def search_patient(
    patient_code: str,
    db: AsyncSession = Depends(get_async_db),
    current_user_id: str = Depends(get_current_user)
):
    """
    Search past predictions/reviews for a patient code.
    """
    if not patient_code:
        raise HTTPException(status_code=400, detail="Patient code is required")
        
    import re
    patient_code = patient_code.strip()
    if not re.match(r"^[a-zA-Z0-9]+$", patient_code):
        raise HTTPException(status_code=400, detail="Mã bệnh nhân chỉ được chứa chữ cái và số viết liền không dấu")

    try:
        return await search_patient_records_service(db, patient_code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

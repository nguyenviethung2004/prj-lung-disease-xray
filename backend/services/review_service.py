from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from sqlalchemy.orm import aliased
from datetime import datetime, timedelta
from models import DoctorReview, Prediction, TrainingFeedback, UploadedImage, Class, User, AIModel
from schemas.lung_disease_schema import DoctorReviewCreate
from core.exceptions import NotFoundException

async def submit_review_service(db: AsyncSession, data: DoctorReviewCreate):
    # 1. Check if prediction exists
    query_pred = select(Prediction).where(Prediction.PredictionID == data.PredictionID)
    result_pred = await db.execute(query_pred)
    prediction = result_pred.scalar_one_or_none()
    
    if not prediction:
        raise NotFoundException("Prediction not found")

    # 2. Create DoctorReview
    new_review = DoctorReview(
        PredictionID=data.PredictionID,
        DoctorID=data.DoctorID,
        FinalClassID=data.FinalClassID,
        DoctorNote=data.DoctorNote,
        IsCorrected=data.IsCorrected,
        BoundingBoxes=data.BoundingBoxes
    )
    db.add(new_review)
    
    # 3. Update UploadedImage status
    query_img = select(UploadedImage).where(UploadedImage.ImageID == prediction.ImageID)
    result_img = await db.execute(query_img)
    uploaded_image = result_img.scalar_one_or_none()
    if uploaded_image:
        uploaded_image.Status = "reviewed"
    
    # 4. If corrected, save to TrainingFeedback
    if data.IsCorrected:
        feedback = TrainingFeedback(
            ImageID=prediction.ImageID,
            OldPredictionID=prediction.PredictedClassID,
            CorrectLabelID=data.FinalClassID,
            UsedForTraining=False
        )
        db.add(feedback)
        
    await db.commit()
    await db.refresh(new_review)
    return new_review

async def get_dashboard_stats_service(db: AsyncSession):
    # 1. General Overview
    total_images = await db.scalar(select(func.count(UploadedImage.ImageID)))
    total_predictions = await db.scalar(select(func.count(Prediction.PredictionID)))
    total_reviews = await db.scalar(select(func.count(DoctorReview.ReviewID)))
    
    total_corrections = await db.scalar(
        select(func.count(DoctorReview.ReviewID))
        .where(DoctorReview.IsCorrected == True)
    )
    
    accuracy = 0
    if total_reviews > 0:
        total_correct = total_reviews - total_corrections
        accuracy = (total_correct / total_reviews) * 100
        
    # 2. Confusion Matrix (Full Data)
    ClassAI = aliased(Class)
    ClassDoctor = aliased(Class)
    
    all_classes_res = await db.execute(select(Class.ClassName).order_by(Class.ClassID))
    class_names = [row[0] for row in all_classes_res.all()]

    query_matrix = (
        select(
            ClassAI.ClassName.label("ai_label"),
            ClassDoctor.ClassName.label("doctor_label"),
            DoctorReview.IsCorrected,
            func.count().label("count")
        )
        .select_from(DoctorReview)
        .join(Prediction, DoctorReview.PredictionID == Prediction.PredictionID)
        .join(ClassAI, Prediction.PredictedClassID == ClassAI.ClassID)
        .join(ClassDoctor, DoctorReview.FinalClassID == ClassDoctor.ClassID)
        .group_by(ClassAI.ClassName, ClassDoctor.ClassName, DoctorReview.IsCorrected)
    )
    matrix_result = await db.execute(query_matrix)
    
    matrix_entries = []
    for row in matrix_result.all():
        matrix_entries.append({
            "ai_label": row.ai_label,
            "doctor_label": row.doctor_label,
            "is_corrected": row.IsCorrected,
            "count": row.count
        })

    # 3. Model Performance
    query_models = (
        select(
            AIModel.ModelName, 
            AIModel.Version, 
            func.count(Prediction.PredictionID).label("pred_count")
        )
        .join(Prediction, AIModel.ModelID == Prediction.ModelID)
        .group_by(AIModel.ModelName, AIModel.Version)
    )
    models_result = await db.execute(query_models)
    model_performance = [
        {"name": row.ModelName, "version": row.Version, "predictions": row.pred_count}
        for row in models_result.all()
    ]

    # 4. Performance Trends (Last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    query_trends = (
        select(
            func.date(DoctorReview.ReviewedAt).label("date"),
            func.count(DoctorReview.ReviewID).label("total"),
            func.sum(case((DoctorReview.IsCorrected == False, 1), else_=0)).label("correct"),
            func.sum(case((DoctorReview.IsCorrected == True, 1), else_=0)).label("errors")
        )
        .where(DoctorReview.ReviewedAt >= seven_days_ago)
        .group_by(func.date(DoctorReview.ReviewedAt))
        .order_by(func.date(DoctorReview.ReviewedAt).asc())
    )
    trends_result = await db.execute(query_trends)
    performance_trends = []
    for row in trends_result.all():
        daily_accuracy = (row.correct / row.total * 100) if row.total > 0 else 0
        performance_trends.append({
            "date": str(row.date),
            "accuracy": round(daily_accuracy, 2),
            "errors": int(row.errors or 0),
            "total": row.total
        })

    return {
        "overview": {
            "total_images": total_images,
            "total_predictions": total_predictions,
            "total_reviews": total_reviews,
            "total_corrections": total_corrections,
            "ai_accuracy_percentage": round(accuracy, 2)
        },
        "confusion_matrix": {
            "labels": class_names,
            "entries": matrix_entries
        },
        "model_performance": model_performance,
        "performance_trends": performance_trends
    }

async def get_all_reviews_service(
    db: AsyncSession, 
    page: int = 1, 
    page_size: int = 10,
    class_id: int = None,
    min_confidence: float = None,
    max_confidence: float = None,
    doctor_id: int = None,
    is_corrected: bool = None,
    start_date: str = None,
    end_date: str = None
):
    ClassAI = aliased(Class)
    ClassDoctor = aliased(Class)
    
    # Base filter conditions
    filters = []
    if class_id:
        filters.append(DoctorReview.FinalClassID == class_id)
    if min_confidence is not None:
        filters.append(Prediction.Confidence >= min_confidence)
    if max_confidence is not None:
        filters.append(Prediction.Confidence <= max_confidence)
    if doctor_id:
        filters.append(DoctorReview.DoctorID == doctor_id)
    if is_corrected is not None:
        filters.append(DoctorReview.IsCorrected == is_corrected)
    if start_date:
        filters.append(DoctorReview.ReviewedAt >= start_date)
    if end_date:
        filters.append(DoctorReview.ReviewedAt <= end_date)

    # 1. Get total count with filters
    total_query = select(func.count(DoctorReview.ReviewID)).join(Prediction, DoctorReview.PredictionID == Prediction.PredictionID)
    if filters:
        total_query = total_query.where(*filters)
    total_count = await db.scalar(total_query)
    
    # 2. Get paginated items with filters
    offset = (page - 1) * page_size
    query = (
        select(
            DoctorReview.ReviewID,
            UploadedImage.ImagePath,
            UploadedImage.OriginalFileName,
            ClassAI.ClassName.label("ai_predicted"),
            ClassDoctor.ClassName.label("doctor_final"),
            Prediction.Confidence,
            DoctorReview.IsCorrected,
            DoctorReview.DoctorNote,
            DoctorReview.ReviewedAt,
            DoctorReview.BoundingBoxes,
            User.UserName.label("doctor_name")
        )
        .select_from(DoctorReview)
        .join(Prediction, DoctorReview.PredictionID == Prediction.PredictionID)
        .join(UploadedImage, Prediction.ImageID == UploadedImage.ImageID)
        .join(ClassAI, Prediction.PredictedClassID == ClassAI.ClassID)
        .join(ClassDoctor, DoctorReview.FinalClassID == ClassDoctor.ClassID)
        .join(User, DoctorReview.DoctorID == User.UserID)
    )
    
    if filters:
        query = query.where(*filters)
        
    query = query.order_by(DoctorReview.ReviewedAt.desc()).limit(page_size).offset(offset)
    
    result = await db.execute(query)
    reviews = []
    for row in result.all():
        reviews.append({
            "id": row.ReviewID,
            "image_path": row.ImagePath,
            "filename": row.OriginalFileName,
            "ai_predicted": row.ai_predicted,
            "doctor_final": row.doctor_final,
            "confidence": row.Confidence,
            "is_corrected": row.IsCorrected,
            "note": row.DoctorNote,
            "reviewed_at": row.ReviewedAt,
            "doctor_name": row.doctor_name,
            "bounding_boxes": row.BoundingBoxes
        })
    
    return {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "items": reviews
    }

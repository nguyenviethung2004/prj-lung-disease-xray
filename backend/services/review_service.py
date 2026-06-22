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

    # 2. Create or Update DoctorReview
    query_existing = select(DoctorReview).where(DoctorReview.PredictionID == data.PredictionID)
    result_existing = await db.execute(query_existing)
    existing_review = result_existing.scalar_one_or_none()

    if existing_review:
        existing_review.DoctorID = data.DoctorID
        existing_review.FinalClassID = data.FinalClassID
        existing_review.DoctorNote = data.DoctorNote
        existing_review.IsCorrected = data.IsCorrected
        existing_review.BoundingBoxes = data.BoundingBoxes
        new_review = existing_review
    else:
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
    
    # 4. If corrected, save or update TrainingFeedback. If not corrected, delete existing TrainingFeedback if any.
    if data.IsCorrected:
        query_feedback = select(TrainingFeedback).where(TrainingFeedback.ImageID == prediction.ImageID)
        result_feedback = await db.execute(query_feedback)
        existing_feedback = result_feedback.scalar_one_or_none()
        
        if existing_feedback:
            existing_feedback.OldPredictionID = prediction.PredictedClassID
            existing_feedback.CorrectLabelID = data.FinalClassID
        else:
            feedback = TrainingFeedback(
                ImageID=prediction.ImageID,
                OldPredictionID=prediction.PredictedClassID,
                CorrectLabelID=data.FinalClassID,
                UsedForTraining=False
            )
            db.add(feedback)
    else:
        query_feedback = select(TrainingFeedback).where(TrainingFeedback.ImageID == prediction.ImageID)
        result_feedback = await db.execute(query_feedback)
        existing_feedback = result_feedback.scalar_one_or_none()
        if existing_feedback:
            await db.delete(existing_feedback)
        
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
    
    # Subquery to get the latest ReviewID for each unique Image
    subq = (
        select(func.max(DoctorReview.ReviewID).label("latest_review_id"))
        .join(Prediction, DoctorReview.PredictionID == Prediction.PredictionID)
        .group_by(Prediction.ImageID)
        .subquery()
    )

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

    # 1. Get total count with filters (explicitly join subq)
    total_query = (
        select(func.count(DoctorReview.ReviewID))
        .join(Prediction, DoctorReview.PredictionID == Prediction.PredictionID)
        .join(subq, DoctorReview.ReviewID == subq.c.latest_review_id)
    )
    if filters:
        total_query = total_query.where(*filters)
    total_count = await db.scalar(total_query)
    
    # 2. Get paginated items with filters (explicitly join subq)
    offset = (page - 1) * page_size
    query = (
        select(
            DoctorReview.ReviewID,
            UploadedImage.ImagePath,
            UploadedImage.OriginalFileName,
            UploadedImage.PatientCode,
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
        .join(subq, DoctorReview.ReviewID == subq.c.latest_review_id)
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
            "patient_code": row.PatientCode,
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


async def search_patient_records_service(db: AsyncSession, patient_code: str):
    ClassAI = aliased(Class)
    ClassDoctor = aliased(Class)
    
    # Subquery to get the latest prediction ID for each image
    subq = (
        select(
            Prediction.ImageID,
            func.max(Prediction.PredictionID).label("latest_pred_id")
        )
        .group_by(Prediction.ImageID)
        .subquery()
    )
    
    # Query all predictions/reviews for the given patient code
    query = (
        select(
            UploadedImage.ImageID,
            UploadedImage.ImagePath,
            UploadedImage.OriginalFileName,
            UploadedImage.UploadedAt,
            UploadedImage.Status,
            UploadedImage.PatientCode,
            Prediction.PredictionID,
            Prediction.Confidence,
            ClassAI.ClassName.label("ai_predicted"),
            DoctorReview.ReviewID,
            ClassDoctor.ClassName.label("doctor_final"),
            DoctorReview.DoctorNote,
            DoctorReview.ReviewedAt,
            DoctorReview.BoundingBoxes
        )
        .select_from(UploadedImage)
        .join(subq, UploadedImage.ImageID == subq.c.ImageID)
        .join(Prediction, Prediction.PredictionID == subq.c.latest_pred_id)
        .join(ClassAI, Prediction.PredictedClassID == ClassAI.ClassID)
        .outerjoin(DoctorReview, Prediction.PredictionID == DoctorReview.PredictionID)
        .outerjoin(ClassDoctor, DoctorReview.FinalClassID == ClassDoctor.ClassID)
        .where(UploadedImage.PatientCode == patient_code)
        .order_by(UploadedImage.UploadedAt.desc())
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    records = []
    for row in rows:
        records.append({
            "image_id": row.ImageID,
            "image_path": row.ImagePath,
            "filename": row.OriginalFileName,
            "uploaded_at": row.UploadedAt,
            "status": row.Status,
            "patient_code": row.PatientCode,
            "prediction_id": row.PredictionID,
            "confidence": row.Confidence,
            "ai_predicted": row.ai_predicted,
            "review_id": row.ReviewID,
            "doctor_final": row.doctor_final if row.ReviewID else None,
            "note": row.DoctorNote if row.ReviewID else None,
            "reviewed_at": row.ReviewedAt if row.ReviewID else None,
            "bounding_boxes": row.BoundingBoxes if row.ReviewID else None
        })
        
    return records


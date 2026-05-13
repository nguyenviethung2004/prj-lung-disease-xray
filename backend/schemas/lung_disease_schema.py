from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

# --- Classes Schemas ---
class ClassBase(BaseModel):
    ClassName: str

class ClassCreate(ClassBase):
    pass

class ClassOut(ClassBase):
    ClassID: int
    class Config:
        from_attributes = True

# --- AIModels Schemas ---
class AIModelBase(BaseModel):
    ModelName: str
    Version: str

class AIModelCreate(AIModelBase):
    pass

class AIModelOut(AIModelBase):
    ModelID: int
    CreatedAt: datetime
    class Config:
        from_attributes = True

# --- UploadedImages Schemas ---
class UploadedImageBase(BaseModel):
    UserID: int
    ImagePath: str
    OriginalFileName: str
    Status: str = "pending"

class UploadedImageCreate(UploadedImageBase):
    pass

class UploadedImageOut(UploadedImageBase):
    ImageID: int
    UploadedAt: datetime
    class Config:
        from_attributes = True

# --- Predictions Schemas ---
class PredictionBase(BaseModel):
    ImageID: int
    ModelID: int
    PredictedClassID: int
    Confidence: float
    HeatmapPath: Optional[str] = None
    InferenceTimeMs: Optional[float] = None

class PredictionCreate(PredictionBase):
    pass

class PredictionOut(PredictionBase):
    PredictionID: int
    CreatedAt: datetime
    class Config:
        from_attributes = True

# --- DoctorReviews Schemas ---
class DoctorReviewBase(BaseModel):
    PredictionID: int
    DoctorID: int
    FinalClassID: int
    DoctorNote: Optional[str] = None
    IsCorrected: bool = False
    BoundingBoxes: Optional[str] = None

class DoctorReviewCreate(DoctorReviewBase):
    pass

class DoctorReviewOut(DoctorReviewBase):
    ReviewID: int
    ReviewedAt: datetime
    class Config:
        from_attributes = True

# --- TrainingFeedback Schemas ---
class TrainingFeedbackBase(BaseModel):
    ImageID: int
    OldPredictionID: int
    CorrectLabelID: int
    UsedForTraining: bool = False

class TrainingFeedbackCreate(TrainingFeedbackBase):
    pass

class TrainingFeedbackOut(TrainingFeedbackBase):
    FeedbackID: int
    CreatedAt: datetime
    class Config:
        from_attributes = True

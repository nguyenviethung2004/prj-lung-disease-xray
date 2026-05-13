from sqlalchemy import Column, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from core.base import Base

class TrainingFeedback(Base):
    __tablename__ = "TrainingFeedback"

    FeedbackID = Column(Integer, primary_key=True, autoincrement=True)
    ImageID = Column(Integer, ForeignKey("UploadedImages.ImageID"), nullable=False)
    OldPredictionID = Column(Integer, ForeignKey("Classes.ClassID"), nullable=False)
    CorrectLabelID = Column(Integer, ForeignKey("Classes.ClassID"), nullable=False)
    UsedForTraining = Column(Boolean, default=False)
    CreatedAt = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<TrainingFeedback(ImageID={self.ImageID}, CorrectLabelID={self.CorrectLabelID})>"

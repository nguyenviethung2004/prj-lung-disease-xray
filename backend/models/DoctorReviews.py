from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.sql import func
from core.base import Base

class DoctorReview(Base):
    __tablename__ = "DoctorReviews"

    ReviewID = Column(Integer, primary_key=True, autoincrement=True)
    PredictionID = Column(Integer, ForeignKey("Predictions.PredictionID"), nullable=False)
    DoctorID = Column(Integer, ForeignKey("Users.UserID"), nullable=False)
    FinalClassID = Column(Integer, ForeignKey("Classes.ClassID"), nullable=False)
    DoctorNote = Column(Text)
    IsCorrected = Column(Boolean, default=False)
    BoundingBoxes = Column(Text, nullable=True) # JSON string of boxes
    ReviewedAt = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<DoctorReview(PredictionID={self.PredictionID}, DoctorID={self.DoctorID}, FinalClassID={self.FinalClassID})>"

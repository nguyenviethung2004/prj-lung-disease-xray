from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, LargeBinary
from sqlalchemy.sql import func
from core.base import Base

class Prediction(Base):
    __tablename__ = "Predictions"

    PredictionID = Column(Integer, primary_key=True, autoincrement=True)
    ImageID = Column(Integer, ForeignKey("UploadedImages.ImageID"), nullable=False)
    ModelID = Column(Integer, ForeignKey("AIModels.ModelID"), nullable=False)
    PredictedClassID = Column(Integer, ForeignKey("Classes.ClassID"), nullable=False)
    Confidence = Column(Float, nullable=False)
    HeatmapPath = Column(String(500))
    InferenceTimeMs = Column(Float)
    AIBoxes = Column(String(2000), nullable=True) # JSON string of AI boxes
    CreatedAt = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Prediction(ImageID={self.ImageID}, PredictedClassID={self.PredictedClassID}, Confidence={self.Confidence})>"

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, LargeBinary
from sqlalchemy.sql import func
from core.base import Base

class UploadedImage(Base):
    __tablename__ = "UploadedImages"

    ImageID = Column(Integer, primary_key=True, autoincrement=True)
    UserID = Column(Integer, ForeignKey("Users.UserID"), nullable=False)
    ImagePath = Column(String(500), nullable=False)
    OriginalFileName = Column(String(255), nullable=False)
    UploadedAt = Column(DateTime, server_default=func.now())
    Status = Column(String(50), server_default="pending") # pending, predicted, reviewed
    PatientCode = Column(String(100), nullable=True) # Mã bệnh nhân

    def __repr__(self):
        return f"<UploadedImage(ImagePath={self.ImagePath}, Status={self.Status}, PatientCode={self.PatientCode})>"

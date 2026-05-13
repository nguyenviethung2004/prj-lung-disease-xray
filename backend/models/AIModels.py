from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from core.base import Base

class AIModel(Base):
    __tablename__ = "AIModels"

    ModelID = Column(Integer, primary_key=True, autoincrement=True)
    ModelName = Column(String(255), nullable=False)
    Version = Column(String(50), nullable=False)
    CreatedAt = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<AIModel(ModelName={self.ModelName}, Version={self.Version})>"

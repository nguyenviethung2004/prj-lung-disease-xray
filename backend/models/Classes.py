from sqlalchemy import Column, Integer, String
from core.base import Base

class Class(Base):
    __tablename__ = "Classes"

    ClassID = Column(Integer, primary_key=True, autoincrement=True)
    ClassName = Column(String(100), nullable=False, unique=True)

    def __repr__(self):
        return f"<Class(ClassName={self.ClassName})>"

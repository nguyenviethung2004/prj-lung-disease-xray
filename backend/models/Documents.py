from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Boolean
from sqlalchemy.dialects.mysql import LONGBLOB
from sqlalchemy.sql import func
from core.base import Base


class Documents(Base):
    __tablename__ = "Documents"

    DocumentID = Column(Integer, primary_key=True, autoincrement=True)

    FileName = Column(String(255), nullable=False)
    FilePath = Column(String(500))
    FileType = Column(String(50))

    UploadedBy = Column(
        Integer,
        ForeignKey("Users.UserID", ondelete="SET NULL"),
        nullable=True
    )

    UploadedAt = Column(
        DateTime,
        server_default=func.now()
    )

    FileSizeMB = Column(Float)
    Description = Column(Text)
    Status = Column(String(20), default='Pending') # Pending, Done
    IsSubmitted = Column(Boolean, default=False)
    FileData = Column(LONGBLOB)

    def save(self, session):
        session.add(self)
        session.commit()
        session.refresh(self)

    def delete(self, session):
        session.delete(self)
        session.commit()

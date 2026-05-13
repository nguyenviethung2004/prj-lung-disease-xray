from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from core.base import Base
from datetime import datetime, timedelta

class PrivateNamespace(Base):
    __tablename__ = "PrivateNamespaces"

    NamespaceID = Column(Integer, primary_key=True, index=True)
    UserID = Column(Integer, nullable=False) # Hoặc ForeignKey("Users.UserID")
    ConversationID = Column(Integer, nullable=False)
    NamespacePath = Column(String(255), nullable=False) # e.g. private:user_id:conv_id
    CreatedAt = Column(DateTime, default=datetime.now)
    ExpireAt = Column(DateTime, nullable=False)

    def is_expired(self):
        return datetime.now() > self.ExpireAt
